from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from neo4j.exceptions import TransientError

from Neo4LDAP.controllers.N4L_Controller import N4LController
from Neo4LDAP.model.N4L_Common import *

import time
import json
import os

MAX_WORKERS = 10
MAX_RETRIES = 15

# Utilities 
def generate_chunks(data):
    chunks = []
    chunks_num = (min(MAX_WORKERS, len(data)))
    chunks_len = len(data) // chunks_num

    ini = 0
    end = chunks_len
    for _ in range (0, chunks_num - 1):
        chunks.append(data[ini:end])
        ini += chunks_len
        end += chunks_len

    chunks.append(data[ini:])
    return chunks

def run_merge_pairs_in_neo4j(session, cypher, pairs):
    try:
        for attempt in range(MAX_RETRIES):
            try:
                session.run(cypher, pairs=pairs)
                break
            except TransientError:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise RuntimeError(traceback.format_exc())
    except Exception:
        raise RuntimeError(traceback.format_exc())
    
def run_merge_in_neo4j(session, cypher, data):
    try:
        for attempt in range(MAX_RETRIES):
            try:
                session.run(cypher, rows=data)
                break
            except TransientError:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise RuntimeError(traceback.format_exc())
    except Exception:
        raise RuntimeError(traceback.format_exc())

def run_match_in_neo4j(session, cypher):
    try:
        for attempt in range(MAX_RETRIES):
            try:
                result = session.run(cypher)
                return result
            except TransientError:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    RuntimeError(traceback.format_exc())
    except Exception:
        raise RuntimeError(traceback.format_exc())
# ---

def create_nodes(session, data, data_type) -> None:
    cypher = f"""
    UNWIND $rows AS row
    MERGE (u:{data_type}:Base {{objectid: row.ObjectIdentifier}})
    SET u += row.Properties
    """

    run_merge_in_neo4j(session, cypher, data)

def generate_indexes(session) -> None:
    indexes = [
        "CREATE CONSTRAINT base_objectid_constraint IF NOT EXISTS FOR (b:Base) REQUIRE b.objectid IS UNIQUE",
        "CREATE CONSTRAINT computer_objectid_constraint IF NOT EXISTS FOR (c:Computer) REQUIRE c.objectid IS UNIQUE",
        "CREATE CONSTRAINT group_objectid_constraint IF NOT EXISTS FOR (g:Group) REQUIRE g.objectid IS UNIQUE",
        "CREATE CONSTRAINT user_objectid_constraint IF NOT EXISTS FOR (u:User) REQUIRE u.objectid IS UNIQUE",
        "CREATE CONSTRAINT gpo_objectid_constraint IF NOT EXISTS FOR (g:GPO) REQUIRE g.objectid IS UNIQUE",
        "CREATE CONSTRAINT container_objectid_constraint IF NOT EXISTS FOR (c:Container) REQUIRE c.objectid IS UNIQUE",
        "CREATE CONSTRAINT ou_objectid_constraint IF NOT EXISTS FOR (o:OU) REQUIRE o.objectid IS UNIQUE",
        "CREATE INDEX user_name_index IF NOT EXISTS FOR (u:User) ON (u.name)",
        "CREATE INDEX computer_name_index IF NOT EXISTS FOR (c:Computer) ON (c.name)",
        "CREATE INDEX group_name_index IF NOT EXISTS FOR (g:Group) ON (g.name)",
        "CREATE INDEX gpo_name_index IF NOT EXISTS FOR (g:GPO) ON (g.name)",
        "CREATE INDEX container_name_index IF NOT EXISTS FOR (c:Container) ON (c.name)",
        "CREATE INDEX ou_name_index IF NOT EXISTS FOR (o:OU) ON (o.name)"
    ]

    for index in indexes:
        session.run(index)        
    
    session.run("CALL db.awaitIndexes()")

# Post processing
def process_laps_sync(session) -> None:
    # Get computers with LAPS
    cypher = """
    MATCH (computer:Computer)
    WHERE computer.haslaps = true
    RETURN computer.objectid AS ObjectIdentifier
    """

    result_laps = run_match_in_neo4j(session, cypher)   
    laps_computers = [record["ObjectIdentifier"] for record in result_laps]

    # Get AdminSDHolder groups (admincount = True)
    cypher = """
    MATCH (group:Group)
    WHERE group.admincount = true
    RETURN group.objectid AS ObjectIdentifier
    """

    result_groups = run_match_in_neo4j(session, cypher)
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
        MATCH (group:Group {objectid: pair.group_id})
        MATCH (computer:Computer {objectid: pair.computer_id})
        MERGE (group)-[:SyncLAPSPassword]->(computer)
        """

        run_merge_pairs_in_neo4j(session, cypher, pairs)

def process_aces(session, data) -> None:
    grouped_by_type = defaultdict(list)

    for node in data:
        target_id = node["ObjectIdentifier"]
        for ace in node.get("Aces", []):
            grouped_by_type[ace["RightName"]].append({
                "PrincipalSID": ace["PrincipalSID"],
                "TargetID": target_id
            })

    for rel_type, rel_data in grouped_by_type.items():
        cypher = f"""
        UNWIND $rows AS row
        MATCH (src:Base {{objectid: row.PrincipalSID}})
        MATCH (dst:Base {{objectid: row.TargetID}})
        MERGE (src)-[r:{rel_type}]->(dst)
        """
        
        run_merge_in_neo4j(session, cypher, rel_data)

def process_trusts(session, data):
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
            MATCH (target_domain:Base {{objectid: $target_domain}})
            MATCH (domain_id:Base {{objectid: $domain_id}})
            {trust}
            """

            session.run(cypher, target_domain=target_domain, domain_id=domain_id)

def process_primary_memberships(session, data):
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

    cypher = """
    UNWIND $rows AS row
    MATCH (member:Base {objectid: row.MemberSID})
    MATCH (group:Group {objectid: row.GroupSID})
    MERGE (member)-[:MemberOf]->(group)
    """
    
    run_merge_in_neo4j(session, cypher, relationships)

# # Sessions and remoting
def process_remote_accounts(session, data, relationship_key, relationship_type, source_node_id = "ObjectIdentifier"):
    relationships = []

    for node in data:
        target_id = node["ObjectIdentifier"]

        for source_id in node.get(relationship_key, []).get("Results", []):
            relationships.append({
                "source_SID": source_id[source_node_id],
                "target_SID": target_id
            })

    cypher = f"""
    UNWIND $rows AS row
    MATCH (source:Base {{objectid: row.source_SID}})
    MATCH (target:Base {{objectid: row.target_SID}})
    MERGE (source)-[:{relationship_type}]->(target)
    """
    
    run_merge_in_neo4j(session, cypher, relationships)

def process_rdp_users(session, data):
    process_remote_accounts(session, data, "RemoteDesktopUsers", "CanRDP")

def process_sessions(session, data):
    process_remote_accounts(session, data, "RegistrySessions", "HasSession", "UserSID")

def process_local_admins(session, data):
    process_remote_accounts(session, data, "LocalAdmins", "AdminTo")

def process_ps_remote(session, data):
    process_remote_accounts(session, data, "PSRemoteUsers", "CanPSRemote")

def process_execute_dcom(session, data):
    process_remote_accounts(session, data, "DcomUsers", "ExecuteDCOM")

def process_computer_remoting(session, data, is_legacy):
    process_sessions(session, data)
    
    if is_legacy :
        process_rdp_users(session, data)
        process_local_admins(session, data)
        process_execute_dcom(session, data)
        process_ps_remote(session, data)

# # ---

def process_relationships(session, data, relationship_key, relationship_type, node_id = "ObjectIdentifier"):
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

    cypher = f"""
    UNWIND $rows AS row
    MATCH (source:Base {{objectid: row.source_SID}})
    MATCH (target:Base {{objectid: row.target_SID}})
    MERGE (source)-[:{relationship_type}]->(target)
    """

    run_merge_in_neo4j(session, cypher, relationships)

def process_gplinks(session, data):
    process_relationships(session, data, "Links", "GPLink", "GUID")

def process_child_objects(session, data):
    process_relationships(session, data, "ChildObjects", "Contains")

def process_memberships(session, data, data_type):
    if data_type == "Group" :
        process_relationships(session, data, "Members", "MemberOf")
    elif data_type == "User" or data_type == "Computer" :
        process_primary_memberships(session, data)

# # Delegation
def process_delegation(session, data, relationship_key, relationship_type, target_node_id = "ObjectIdentifier"):
    relationships = []

    for node in data:
        source_id = node["ObjectIdentifier"]

        for target_id in node.get(relationship_key, []):
            relationships.append({
                "source_SID": source_id,
                "target_SID": target_id[target_node_id]
            })

    cypher = f"""
    UNWIND $rows AS row
    MATCH (source:Base {{objectid: row.source_SID}})
    MATCH (target:Base {{objectid: row.target_SID}})
    MERGE (source)-[:{relationship_type}]->(target)
    """

    run_merge_in_neo4j(session, cypher, relationships)

def process_delegation_for_user(session, data, relationship_key, relationship_type):
    relationships = []

    for node in data:
        source_id = node["ObjectIdentifier"]

        for target_id in node.get(relationship_key, []):
            relationships.append({
                "source_SID": source_id,
                "target_SID": target_id
            })

    cypher = f"""
    UNWIND $rows AS row
    MATCH (source:Base {{objectid: row.source_SID}})
    MATCH (target:Base {{objectid: row.target_SID}})
    MERGE (source)-[:{relationship_type}]->(target)
    """
    run_merge_in_neo4j(session, cypher, relationships)

def process_constrained_delegation(session, data):
    process_delegation(session, data, "AllowedToDelegate", "AllowedToDelegate")

def process_rbcd(session, data):
    process_delegation(session, data, "AllowedToAct", "AllowedToAct")

def process_computer_delegation(session, data):
    process_constrained_delegation(session, data)
    process_rbcd(session, data)

def process_user_constrained_delegation(session, data):
    process_delegation_for_user(session, data, "AllowedToDelegate", "AllowedToDelegate")

def process_user_delegation(session, data):
    process_user_constrained_delegation(session, data)

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

def postprocess(session, data, data_type, is_legacy) -> None:
    process_memberships(session, data, data_type)
    process_aces(session, data)

    if data_type == "Container" or data_type == "OU" :
        process_child_objects(session, data)
        process_gplinks(session, data)

    if data_type == "Computer" :
        process_computer_remoting(session, data, is_legacy)
        process_computer_delegation(session, data)

    if data_type == "User" :
        process_user_delegation(session, data)

    if data_type == "Domain" :
        process_trusts(session, data)

    if data_type == "Group" :
        process_laps_sync(session)

def upload_data(json_files, workers, retries, is_legacy) -> None:
    global MAX_RETRIES, MAX_WORKERS

    MAX_RETRIES = retries
    MAX_WORKERS = workers

    current_exception = ""

    controller = N4LController().get_instance()
    exception_on_upload = False

    grouped_files = defaultdict(list)
    for path in json_files:
        dir_path = os.path.dirname(path)
        file_name = os.path.basename(path)
        grouped_files[dir_path].append((path, file_name))

    push_debug_info("::: GENERATING INDEXES :::\n")
    with Neo4jConnector.driver.session(database=Neo4jConnector.database) as session:
        generate_indexes(session)
    push_debug_info("    [✔] Indexes generated\n")

    push_debug_info("::: CREATING NODES :::\n")
    for group_path, file_list in grouped_files.items():
        push_debug_info("  # {directory_path}".format(directory_path = group_path))
        for full_path, file_name in file_list:
            try:
                data, data_type = retrieve_json_info(full_path)
                with Neo4jConnector.driver.session(database=Neo4jConnector.database) as session:
                    create_nodes(session, data, data_type)

                push_debug_info("    [✔] {file}".format(file = file_name))
            except:
                current_exception = traceback.format_exc()
                push_debug_info("    [✘] {file}".format(file = file_name))
                exception_on_upload = True

                break
        
        push_debug_info("")
    
    if not exception_on_upload:
        
        push_debug_info("::: POST PROCESSING :::\n")
        for group_path, file_list in grouped_files.items():
            push_debug_info("  # {directory_path}".format(directory_path = group_path))
            for full_path, file_name in file_list:
                try:
                    data, data_type = retrieve_json_info(full_path)    
                    chunks = generate_chunks(data)

                    push_debug_info("    [#] Post-Processing {file}".format(file = file_name))
                    
                    # One session - Chunk (MAX_WORKERS)
                    sessions = []
                    for _ in range(0, len(chunks)):
                        sessions.append(Neo4jConnector.driver.session(database=Neo4jConnector.database))

                    # MAX_WORKERS Threads
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = []

                        for i, chunk in enumerate(chunks):
                            futures.append(executor.submit(postprocess, sessions[i], chunk, data_type, is_legacy))

                        for future in as_completed(futures):
                            future.result()  

                    push_debug_info("    [✔] {file}".format(file = file_name))

                    for session in sessions:
                        session.close()

                except:
                    current_exception = traceback.format_exc()
                    push_debug_info("    [✘] {file}".format(file = file_name))
                    exception_on_upload = True
                    break          
            
            push_debug_info("")
            if(exception_on_upload):
                break

        if(not exception_on_upload):
            push_debug_info("=== COMPLETED ===\n")
        else:
            push_debug_info("=== ERROR ===\n")
            controller.notify_error(current_exception)
    else:
        push_debug_info("=== ERROR ===\n")
        controller.notify_error(current_exception)

    controller.update_neo4j_db_stats()