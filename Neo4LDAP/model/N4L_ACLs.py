from Neo4LDAP.model.N4L_Common import *
from Neo4LDAP.controllers.N4L_Controller import N4LController
from collections import defaultdict

import networkx as nx
import heapq

class ACLGraph:
    
    ACL_VALUE = {
        "CanPSRemote": 4,
        "CanRDP": 4,
        "HasSession": 4,
        "Contains": 1,
        "DCSync": 3,
        "DumpSMSAPassword": 4,
        "ExecuteDCOM": 1,
        "ForceChangePassword": 2,
        "GenericAll": 3,
        "GenericWrite": 3,
        "GetChanges": 1,
        "GetChangesAll": 1,
        "GetChangesInFilteredSet": 1,
        "GPLink": 1,
        "Owns": 3,
        "ReadGMSAPassword": 4,
        "ReadLAPSPassword": 4,
        "SyncLapsPassword": 4,
        "WriteDACL": 3,
        "WriteOwner": 3,
        "WriteSPN": 2,
        "AddMember": 4,
        "AdmintTo": 4,
        "AllowedToAct": 3,
        "AllowedToDelegate": 3,
        "MemberOf": 5,
    }

    def __init__(self):
        self.graph = nx.DiGraph()
        self.depth_by_node = {}
        self.acls_by_nodes = defaultdict(lambda: defaultdict(list))

    def add_relationship(self, source, relationship, target) -> None:
        self.graph.add_edge(source, target, relationship=relationship)
    
    def remove_relationship(self, source, relationship, target) -> None:
        self.graph.remove_edge(source, target, relationship=relationship)

    # GRAPH POPULATION    
    def is_path_better(self, candidate, current_best) -> bool:
        if current_best is None:
            return True

        avg_candidate = sum(candidate) / len(candidate)
        avg_best = sum(current_best) / len(current_best)

        # 1- Best average is better
        if avg_candidate != avg_best:
            return avg_candidate > avg_best

        # 2- On equal average, shortest path is better
        if len(candidate) != len(current_best):
            return len(candidate) < len(current_best)

        # 3- On equal average and path length, bigger minimum value is better 
        return min(candidate) > min(current_best)

    def compute_best_paths_with_cycles(self, start_node) -> dict:
        best_path   = defaultdict(lambda: None)
        best_parent = {}
        protected_nodes = set()
        best_path[start_node] = []

        # bigger sum -> less path length -> bigger minimum value 
        def make_priority(path_values):
            if path_values : # negative values -> heapq inverse popup logic, minimum is at top
                return (-sum(path_values), len(path_values), -min(path_values))
            else:
                return 0

        heap = [(make_priority(best_path[start_node]), start_node)]

        while heap:
            _, current = heapq.heappop(heap)
            current_path = best_path[current]

            for neighbor in self.graph.successors(current):
                acls = ",".join(self.acls_by_nodes[current][neighbor])
                weight = 0

                # If a node has multiple acls, the bigger value is taken as the weight
                for acl in self.acls_by_nodes[current][neighbor]: 
                    weight = max(weight, self.ACL_VALUE.get(acl, 1))

                new_path = current_path + [weight]

                # Always include first degree targets if the weighted acl is at least 3
                if current == start_node and weight >= 3:
                    best_path[neighbor] = [weight]
                    best_parent[neighbor] = (current, acls)
                    protected_nodes.add(neighbor)

                    heapq.heappush(heap, (make_priority([weight]), neighbor))
                    continue

                # First degree node
                if neighbor in protected_nodes:
                    continue

                if self.is_path_better(new_path, best_path[neighbor]):
                    best_path[neighbor] = new_path
                    best_parent[neighbor] = (current, acls)
                    heapq.heappush(heap, (make_priority(new_path), neighbor))

        return best_parent
    
    def creates_cycle(self, dag, source, target) -> bool:
        try:
            temp_graph = dag.graph.copy()
            temp_graph.add_edge(source, target)
            nx.find_cycle(temp_graph, orientation="original")
            return True
        except nx.NetworkXNoCycle:
            return False
        
    def compute_shadow_relationships(self) -> None:
        hidden_counts = {}
        for source, targets in self.acls_by_nodes.items():
            for target, _ in targets.items():
                acls = ",".join(self.acls_by_nodes[source][target])

                if "MemberOf" in acls:
                    continue
                
                if self.graph.has_edge(source, target) :
                    if self.graph[source][target].get("relationship") != acls :
                        hidden_counts[source] = hidden_counts.get(source, 0) + 1
                else:
                    hidden_counts[source] = hidden_counts.get(source, 0) + 1

        nx.set_node_attributes(self.graph, hidden_counts, "shadow_relationships")
    
    def compute_dag_graph(self, name, inbound_check) -> None:
        dag = ACLGraph()
        dag.graph.add_nodes_from(self.graph.nodes(data=True))

        best_parent = self.compute_best_paths_with_cycles(name)
        
        if not inbound_check :
            for target, (source, acl_label) in best_parent.items():
                dag.add_relationship(source, acl_label, target)

                if self.creates_cycle(dag, source, target) :
                    dag.graph.remove_edge(source, target)

        elif inbound_check:
            for node in self.graph.nodes:
                for pred in self.graph.predecessors(node):
                    acls = ",".join(self.acls_by_nodes[pred][node])
                    dag.add_relationship(pred, acls, node)

        self.graph = dag.graph

        # The DAG creation can hide some duplicated acls, that acls are indicated as shadow relationships
        self.compute_shadow_relationships()


    def populate_graph(self, result, name, exclusion_list = None, inbound_check = False, targeted_search = False, enriched_acls = []) -> list:
        node_list = []

        for record in result:
            path = record["path"]

            nodes = path.nodes
            relationships = path.relationships

            if len(nodes) < 2 or len(relationships) < 1:
                continue

            for node in nodes:
                node_fullname, node_type, node_id = self.retrieve_node_identity(node)

                if (node_fullname not in self.graph) and ((exclusion_list == None) or (exclusion_list != None and node_fullname not in exclusion_list)) :
                    self.graph.add_node(node_fullname, node_type=node_type, node_id = node_id)
                    node_list.append(node_fullname)

            for relationship in relationships:
                source_node = relationship.nodes[0]
                target_node = relationship.nodes[1]
                acl = relationship.type

                source, _, _ = self.retrieve_node_identity(source_node)
                target, _, _ = self.retrieve_node_identity(target_node)

                if inbound_check :
                    if (exclusion_list == None) or (exclusion_list != None and source not in exclusion_list) :
                        if acl not in self.acls_by_nodes[source][target] :
                            self.acls_by_nodes[source][target].append(acl)
                else:
                    if (exclusion_list == None) or (exclusion_list != None and target not in exclusion_list) :
                        if target.upper() != name.upper() :
                            if acl not in self.acls_by_nodes[source][target] :
                                self.acls_by_nodes[source][target].append(acl)
                
                if targeted_search :
                    for enriched_acl in enriched_acls:
                        source, target, acls = enriched_acl

                        for acl in acls:
                            if acl not in self.acls_by_nodes[source][target] :
                                self.acls_by_nodes[source][target].append(acl)


        # Custom ACLs
        replacement_rules = {
            ("GetChanges", "GetChangesAll"): "DCSync",
            ("GetChanges", "GetChangesInFilteredSet"): "SyncLAPSPassword"
        }

        for _, targets in self.acls_by_nodes.items():
            for _, acl_list in list(targets.items()):
                acl_set = set(acl_list)
                remove_set = set()
                add_set = set()

                for required_acls, replacement_acl in replacement_rules.items():
                    has_all_acls = True
                    for acl in required_acls:
                        if acl not in acl_set:
                            has_all_acls = False
                            break

                    if has_all_acls :
                        add_set.add(replacement_acl)
                        remove_set.update(required_acls)

                # Re ingest the acls without the deleted ones
                updated_acl_list = []
                for acl in acl_list:
                    if acl not in remove_set:
                        updated_acl_list.append(acl)

                for acl in add_set:
                    if acl not in acl_list:
                        updated_acl_list.append(acl)

                acl_list[:] = updated_acl_list

        return node_list
    
    # ---

    def process_graph_acls(self) -> None:
        for source in self.acls_by_nodes.keys():
            for target in self.acls_by_nodes[source].keys():
                self.add_relationship(source, ",".join(self.acls_by_nodes[source][target]), target)
    
    def retrieve_node_identity(self, node) -> tuple:
        node_type = list(node.labels)
        node_type.remove("Base")

        node_id = node.get("objectid", "UNKNOWN")
        
        if node_type[0] == "Domain" :
            return node.get("domain", "UNKNOWN"), node_type[0], node_id
        else:
            fullname = node.get("name", "UNKNOWN")

            return fullname, node_type[0], node_id

def draw_acl_graph(graph, name, inbound_check) -> None:
    root_node = ""
    for node in graph.nodes(data=False):        
        if node.lower() == name.lower():
           root_node = node

    controller = N4LController().get_instance()
    controller.redraw_ACL_graph(graph, root_node, inbound_check)

def retrieve_acls_by_depth(acl_graph, name, root_node, acl_list, depth, level, exclusion_list = None) -> None:
    with Neo4jConnector.driver.session() as session:
        try:
            query = """
            MATCH (n) 
            WHERE toUpper(n.name) = toUpper('{name}') 
            MATCH (m) 
            WHERE NOT m.name = n.name 
            MATCH p=(n)-[r:{acl}*..1]->(m)
            RETURN p as path
            """.format(name = name, acl = acl_list)

            result = session.run(query)
            nodes = acl_graph.populate_graph(result, root_node, exclusion_list)
            if level < depth :
                for node in nodes:
                    retrieve_acls_by_depth(acl_graph, node, root_node, acl_list, depth, level + 1, exclusion_list)   
        except:
            controller = N4LController().get_instance()
            controller.notify_error(traceback.format_exc())

def retrieve_acls_by_target(acl_graph, source_node, target_node, acl_list, exclusion_list = None) -> None:
    with Neo4jConnector.driver.session() as session:
        try:
            query = """
            MATCH (n)
            WHERE toUpper(n.name) = toUpper('{source_node}')
            MATCH (m)
            WHERE toUpper(m.name) = toUpper('{target_node}')
            MATCH p = shortestPath((n)-[r:{acl}*]->(m))
            RETURN p as path
            """.format(source_node = source_node, target_node = target_node, acl = acl_list)
            
            result = session.run(query)

            node_pairs = []
            for record in result:
                path = record["path"]
                nodes = path.nodes
                for i in range(len(nodes) - 1):
                    node_pairs.append((nodes[i]["name"].upper(), nodes[i + 1]["name"].upper()))


            acl_enrichment_query = """
            UNWIND $pairs AS pair
            MATCH (n)
            WHERE toUpper(n.name) = toUpper(pair[0])
            MATCH (m)
            WHERE toUpper(m.name) = toUpper(pair[1])
            MATCH (n)-[r:{acl}*..1]->(m)
            UNWIND r AS rel
            RETURN n.name AS source, m.name AS target, collect(DISTINCT type(rel)) AS acls
            """.format(acl = acl_list)

            enrichment_result = session.run(acl_enrichment_query, {"pairs": node_pairs})
            
            enriched_acls = []
            for record in enrichment_result:
                enriched_acls.append((record["source"], record["target"], record["acls"]))

            result = session.run(query)
            acl_graph.populate_graph(result, source_node, exclusion_list, False, True, enriched_acls)

        except:
            controller = N4LController().get_instance()
            controller.notify_error(traceback.format_exc())

def retrieve_inbound_acls(acl_graph, name, root_node, acl_list, exclusion_list = None) -> None:
    with Neo4jConnector.driver.session() as session:
        try:
            query = """
            MATCH (n) 
            WHERE toUpper(n.name) = toUpper('{name}') 
            MATCH (m) 
            WHERE NOT m.name = n.name 
            MATCH p=(n)<-[r:{acl}*..1]-(m)
            RETURN p as path
            """.format(name = name, acl = acl_list)
                
            result = session.run(query)
            acl_graph.populate_graph(result, root_node, exclusion_list, True)
        except:
            controller = N4LController().get_instance()
            controller.notify_error(traceback.format_exc())

def retrieve_acl_list(acls) -> list:
    controller = N4LController().get_instance()
    neo4j_acls = controller.retrieve_neo4j_stats()["ACL_Types"]
    
    valid_acls = {}
    for acl in neo4j_acls:
        valid_acls[acl.lower()] = acl

    acl_list_lower = [acl.lower() for acl in acls]
    acl_list = ""

    if len(acls) > 1 :
        for acl in acl_list_lower:
            acl_list += valid_acls[acl] + "|"

        acl_list = acl_list[:-1]
    else:
        if acl_list_lower[0] == "all" :
            for acl in valid_acls.values():
                if acl != "Contains" :
                    acl_list += acl + "|"
            
            acl_list = acl_list[:-1]
        elif acl_list_lower[0] == "firstdegree" :
            for acl in valid_acls.values():
                if acl != "MemberOf" :
                    acl_list += acl + "|"
            
            acl_list = acl_list[:-1]
        else:
            acl_list = valid_acls[acl_list_lower[0]]
    
    return acl_list

def check_acls(name, acls, depth, source_node, target_node, exclusion_list = None, inbound_check = False, targeted_check = False) -> None:
    try:
        acl_graph = ACLGraph()
        acl_list = retrieve_acl_list(acls)

        root_node = name

        targeted_search = targeted_check
        inbound_search = inbound_check
        outbound_search = False

        if not targeted_search and not inbound_search :
            outbound_search = True
        
        if outbound_search :
            if depth == '' :
                depth = 100
            else:
                depth = int(depth)

            retrieve_acls_by_depth(acl_graph, name, name, acl_list, depth, 1, exclusion_list)
        elif inbound_search :
            retrieve_inbound_acls(acl_graph, name, name, acl_list, exclusion_list)
        elif targeted_search :
            root_node = source_node
            retrieve_acls_by_target(acl_graph, source_node, target_node, acl_list, exclusion_list)


        if len(acl_graph.graph) != 0 :
            acl_graph.process_graph_acls()
            if outbound_search or inbound_search :
                acl_graph.compute_dag_graph(name, inbound_check)

            draw_acl_graph(acl_graph.graph, root_node, inbound_check)
        else:
            controller = N4LController().get_instance()
            controller.notify_no_results("ACL Finder didn't return any result")
    except:
        controller = N4LController().get_instance()
        controller.notify_error(traceback.format_exc())