from collections import defaultdict

from Neo4LDAP.controllers.N4L_Controller import N4LController
from Neo4LDAP.model.N4L_Common import *

import json
import os

# Utilities 
def chunked_data(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]

# ---

def create_nodes(data, data_type) -> None:
    for batch in chunked_data(data, 100):
        cypher = f"""
        UNWIND $rows AS row
        MERGE (u:{data_type}:Base {{objectid: row.ObjectIdentifier}})
        SET u += row.Properties
        """
    
        with Neo4jConnector.driver.session() as session:
            session.run(cypher, rows=batch)

# Post processing
def process_laps_sync() -> None:
    # Get computers with LAPS
    cypher = """
    MATCH (c:Computer)
    WHERE c.haslaps = true
    RETURN c.objectid AS ObjectIdentifier
    """

    laps_computers = ""
    with Neo4jConnector.driver.session() as session:
        result_laps = session.run(cypher)
        laps_computers = [record["ObjectIdentifier"] for record in result_laps]

    # Get AdminSDHolder groups (admincount = True)
    cypher = """
    MATCH (g:Group)
    WHERE g.admincount = true
    RETURN g.objectid AS ObjectIdentifier
    """

    privileged_groups = ""
    with Neo4jConnector.driver.session() as session:
        result_groups = session.run(cypher)
        privileged_groups = [record["ObjectIdentifier"] for record in result_groups]

    pairs = []
    default_dcsync_groups = ["-512", "-516", "-519", "-544"]

    for group_id in privileged_groups:
        for computer_id in laps_computers:
            if group_id.endswith(tuple(default_dcsync_groups)) :
                pair = {
                    "group_id": group_id,
                    "computer_id": computer_id
                }
                pairs.append(pair)
    
    if pairs:
        cypher = """
        UNWIND $pairs AS pair
        MATCH (g:Group {objectid: pair.group_id})
        MATCH (c:Computer {objectid: pair.computer_id})
        MERGE (g)-[:SyncLAPSPassword]->(c)
        """
        with Neo4jConnector.driver.session() as session:
            session.run(cypher, pairs=pairs)

def process_aces(data) -> None:
    grouped_by_type = defaultdict(list)

    for node in data:
        target_id = node["ObjectIdentifier"]
        for ace in node.get("Aces", []):
            grouped_by_type[ace["RightName"]].append({
                "PrincipalSID": ace["PrincipalSID"],
                "TargetID": target_id
            })

    for rel_type, rel_data in grouped_by_type.items():
        for batch in chunked_data(rel_data, 100):
            cypher = f"""
            UNWIND $rows AS row
            MATCH (src {{objectid: row.PrincipalSID}})
            MATCH (dst {{objectid: row.TargetID}})
            MERGE (src)-[r:{rel_type}]->(dst)
            """
            with Neo4jConnector.driver.session() as session:
                session.run(cypher, rows=batch)

def process_trusts(data):
    for node in data:
        domain_id = node["ObjectIdentifier"]

        for child in node.get("Trusts", []):
            target_domain = child["TargetDomainSid"]
            direction = child["TrustDirection"]

            trust = ""
            if direction == 1 or direction == "Inbound" :
                trust = "MERGE (domain_id)-[:TrustedBy]->(target_domain)"
            elif direction == 2 or direction == "Outbound" :
                trust = "MERGE (target_domain)-[:TrustedBy]->(domain_id)"
            elif direction == 3 or direction == "Bidirectional" :
                trust = """
                MERGE (domain_id)-[:TrustedBy]->(target_domain)
                MERGE (target_domain)-[:TrustedBy]->(domain_id)
                """

            cypher = f"""
            MATCH (target_domain {{objectid: $target_domain}})
            MATCH (domain_id {{objectid: $domain_id}})
            {trust}
            """

            with Neo4jConnector.driver.session() as session:
                session.run(cypher, target_domain=target_domain, domain_id=domain_id)

def process_primary_memberships(data):
    relationships = []

    for node in data:
        member_id = node["ObjectIdentifier"]

        # PrimaryGroupSID relationship
        primary_group_sid = node.get("PrimaryGroupSID")
        if primary_group_sid:
            relationships.append({
                "MemberSID": member_id,               
                "GroupSID": primary_group_sid
            })

    for batch in chunked_data(relationships, 100):
        cypher = """
        UNWIND $rows AS row
        MATCH (member {objectid: row.MemberSID})
        MATCH (group {objectid: row.GroupSID})
        MERGE (member)-[:MemberOf]->(group)
        """
        with Neo4jConnector.driver.session() as session:
            session.run(cypher, rows=batch)

# # Sessions and remoting
def process_remote_accounts(data, relationship_key, relationship_type, source_node_id = "ObjectIdentifier"):
    relationships = []

    for node in data:
        target_id = node["ObjectIdentifier"]

        for source_id in node.get(relationship_key, []).get("Results", []):
            relationships.append({
                "source_SID": source_id[source_node_id],
                "target_SID": target_id
            })

    for batch in chunked_data(relationships, 100):
        cypher = f"""
        UNWIND $rows AS row
        MATCH (source {{objectid: row.source_SID}})
        MATCH (target {{objectid: row.target_SID}})
        MERGE (source)-[:{relationship_type}]->(target)
        """
        
        with Neo4jConnector.driver.session() as session:
            session.run(cypher, rows=batch)

def process_rdp_users(data):
    process_remote_accounts(data, "RemoteDesktopUsers", "CanRDP")

def process_sessions(data):
    process_remote_accounts(data, "RegistrySessions", "HasSession", "UserSID")

def process_local_admins(data):
    process_remote_accounts(data, "LocalAdmins", "AdminTo")

def process_ps_remote(data):
    process_remote_accounts(data, "PSRemoteUsers", "CanPSRemote")

def process_execute_dcom(data):
    process_remote_accounts(data, "DcomUsers", "ExecuteDCOM")

def process_computer_remoting(data, is_legacy):
    process_sessions(data)
    
    if is_legacy :
        process_rdp_users(data)
        process_local_admins(data)
        process_execute_dcom(data)
        process_ps_remote(data)

# # ---

def process_relationships(data, relationship_key, relationship_type, node_id = "ObjectIdentifier"):
    relationships = []

    for node in data:
        target_id = node["ObjectIdentifier"]

        for nodes in node.get(relationship_key, []):
            if relationship_type == "Contains" :
                relationships.append({
                    "source_SID": target_id,
                    "target_SID": nodes[node_id]
                })
            else:  
                relationships.append({
                    "source_SID": nodes[node_id],
                    "target_SID": target_id
                })

    for batch in chunked_data(relationships, 100):
        cypher = f"""
        UNWIND $rows AS row
        MATCH (source {{objectid: row.source_SID}})
        MATCH (target {{objectid: row.target_SID}})
        MERGE (source)-[:{relationship_type}]->(target)
        """
        
        with Neo4jConnector.driver.session() as session:
            session.run(cypher, rows=batch)

def process_gplinks(data):
    process_relationships(data, "Links", "GPLink", "GUID")

def process_child_objects(data):
    process_relationships(data, "ChildObjects", "Contains")

def process_memberships(data, data_type):
    if data_type == "Group" :
        process_relationships(data, "Members", "MemberOf")
    elif data_type == "User" or data_type == "Computer" :
        process_primary_memberships(data)

# # Delegation
def process_delegation(data, relationship_key, relationship_type, target_node_id = "ObjectIdentifier"):
    relationships = []

    for node in data:
        source_id = node["ObjectIdentifier"]

        for target_id in node.get(relationship_key, []):
            relationships.append({
                "source_SID": source_id,
                "target_SID": target_id[target_node_id]
            })

    for batch in chunked_data(relationships, 100):
        cypher = f"""
        UNWIND $rows AS row
        MATCH (source {{objectid: row.source_SID}})
        MATCH (target {{objectid: row.target_SID}})
        MERGE (source)-[:{relationship_type}]->(target)
        """
        
        with Neo4jConnector.driver.session() as session:
            session.run(cypher, rows=batch)

def process_delegation_for_user(data, relationship_key, relationship_type):
    relationships = []

    for node in data:
        source_id = node["ObjectIdentifier"]

        for target_id in node.get(relationship_key, []):
            relationships.append({
                "source_SID": source_id,
                "target_SID": target_id
            })

    for batch in chunked_data(relationships, 100):
        cypher = f"""
        UNWIND $rows AS row
        MATCH (source {{objectid: row.source_SID}})
        MATCH (target {{objectid: row.target_SID}})
        MERGE (source)-[:{relationship_type}]->(target)
        """
        
        with Neo4jConnector.driver.session() as session:
            session.run(cypher, rows=batch)

def process_constrained_delegation(data):
    process_delegation(data, "AllowedToDelegate", "AllowedToDelegate")

def process_rbcd(data):
    process_delegation(data, "AllowedToAct", "AllowedToAct")

def process_computer_delegation(data):
    process_constrained_delegation(data)
    process_rbcd(data)

def process_user_constrained_delegation(data):
    process_delegation_for_user(data, "AllowedToDelegate", "AllowedToDelegate")

def process_user_delegation(data):
    process_user_constrained_delegation(data)

# # ---
# ---

def readJsonFile(json_file) -> json:
    with open(json_file, 'r', encoding='utf-8-sig') as file:
        data = json.load(file)

    return data

def retrieve_json_info(json_file):
    data_raw = readJsonFile(json_file)

    data_type_raw = data_raw["meta"]["type"]
    
    data_type = ""
    if data_type_raw == "ous" or data_type_raw == "gpos" :
        data_type = data_type_raw.upper()[0:-1]
    else:
        data_type = data_type_raw[0].upper() + data_type_raw[1:-1]

    data = data_raw["data"]

    return data, data_type

def push_debug_info(message) -> None:
    controller = N4LController().get_instance()
    controller.push_upload_debug_info(message)

def upload_data(json_files, is_legacy) -> None:
    controller = N4LController().get_instance()

    exception_on_upload = False

    grouped_files = defaultdict(list)
    for path in json_files:
        dir_path = os.path.dirname(path)
        file_name = os.path.basename(path)
        grouped_files[dir_path].append((path, file_name))

    push_debug_info("::: CREATING NODES :::\n")
    for group_path, file_list in grouped_files.items():
        push_debug_info("  # {directory_path}".format(directory_path = group_path))
        for full_path, file_name in file_list:
            try:
                data, data_type = retrieve_json_info(full_path)
                create_nodes(data, data_type)
                push_debug_info("    [✔] {file}".format(file = file_name))
            except:
                push_debug_info("    [✘] {file}".format(file = file_name))
                exception_on_upload = True

                from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
                N4LMessageBox("Error", traceback.format_exc(), controller.retrieve_main_window(), 600, 500)
                
                break
        
        push_debug_info("")

    if not exception_on_upload:
        push_debug_info("::: POST PROCESSING :::\n")

        for group_path, file_list in grouped_files.items():
            push_debug_info("  # {directory_path}".format(directory_path = group_path))
            for full_path, file_name in file_list:
                try:
                    data, data_type = retrieve_json_info(full_path)

                    process_memberships(data, data_type)
                    process_aces(data)
                    
                    if data_type == "Container" or data_type == "OU" :
                        process_child_objects(data)
                        process_gplinks(data)

                    if data_type == "Computer" :
                        process_computer_remoting(data, is_legacy)
                        process_computer_delegation(data)

                    if data_type == "User" :
                        process_user_delegation(data)

                    if data_type == "Domain" :
                        process_trusts(data)

                    if data_type == "Group" :
                        process_laps_sync()

                    push_debug_info("    [✔] {file}".format(file = file_name))
                except:
                    push_debug_info("    [✘] {file}".format(file = file_name))
                    exception_on_upload = True

                    from Neo4LDAP.gui.N4L_Popups import N4LMessageBox
                    N4LMessageBox("Error", traceback.format_exc(), controller.retrieve_main_window(), 600, 500)

                    break

            push_debug_info("")

    controller.update_neo4j_db_stats()