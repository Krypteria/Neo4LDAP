from neo4j import GraphDatabase

import traceback

class Neo4jConnector:
    driver = None

    @staticmethod
    def connect_to_neo4j(username, password, uri) -> object:
        try:
            Neo4jConnector.driver = GraphDatabase.driver(uri, auth=(username, password), encrypted=False)
            with Neo4jConnector.driver.session() as session:
                session.run("MATCH (n) RETURN n LIMIT 1")
        except:
            from Neo4LDAP.controllers.N4L_Controller import N4LController

            controller = N4LController().get_instance()
            controller.notify_error(traceback.format_exc())

    @staticmethod
    def retrieve_neo4j_stats() -> dict:
        with Neo4jConnector.driver.session() as session:
            neo4j_stats = {}

            # ACL types
            result = session.run("CALL db.relationshipTypes()")

            acl_types = []
            for record in result:
                acl_types.append(record["relationshipType"])

            neo4j_stats["ACL_Types"] = sorted(acl_types)

            # ACLs and relationships
            neo4j_stats["Relationships"] = session.run("MATCH ()-[r]->() RETURN count(r) AS rel_count").single()["rel_count"]
            neo4j_stats["ACLs"] = session.run("""
            MATCH ()-[r]->() 
            WHERE type(r) IN {acls}  
            RETURN count(r) as acl_count;
            """.format(acls = neo4j_stats["ACL_Types"])).single()["acl_count"]

            for on_premise_item in ["User", "Group", "Computer", "OU", "GPO", "Domain"]:
                count = session.run(f"MATCH (n:{on_premise_item}) RETURN count(n) AS count").single()["count"]
                neo4j_stats[on_premise_item] = count

            return neo4j_stats
    
    @staticmethod
    def clear_neo4j_db_data() -> None:
        with Neo4jConnector.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")