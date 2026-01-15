from datetime import datetime, timezone, timedelta

from Neo4LDAP.model.N4L_Common import *
from Neo4LDAP.controllers.N4L_Controller import N4LController

import re

def parse_timestamp(timestamp) -> datetime:
    try:
        time_value = str(timestamp).strip()
        return_format = '%d-%m-%Y %H:%M:%S'

        # GeneralizedTime -> YYYYMMDDHHMMSS(.0)Z
        if time_value.endswith("Z") and len(time_value) >= 15 :
            try:
                return datetime.strptime(time_value, "%Y%m%d%H%M%S.%fZ").strftime(return_format)
            except ValueError:
                return datetime.strptime(time_value, "%Y%m%d%H%M%SZ").strftime(return_format)

        # Windows FILETIME -> 100ns intervals since Jan 1, 1601
        time_value_int = int(float(time_value))
        if time_value_int > 100000000000000000:
            if time_value_int == 0:
                return "Never"
            date = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=time_value_int // 10)
            return date.strftime(return_format)

        # Unix timestamp (epoch)
        date = datetime.fromtimestamp(time_value_int, tz=timezone.utc)
        return date.strftime(return_format)
    except Exception:
        return "Invalid timestamp"

#Some LDAP keys doesn't exist in cypher so we need to adapt them
def adapt_ldap_item_to_cypher(member_key, member_value) -> tuple:
    member_value = member_value.upper().strip()
    member_key = member_key.lower().strip()

    if member_key == "cn" :
        cypher_key = "toUpper(n.name)"
    elif member_key == "objectclass" :
        if member_value == "*" :
            cypher_key = "n.samaccountname"
        elif member_value == "ORGANIZATIONALUNIT" :
            cypher_key = "ou.name"
            member_value = "*"
        elif member_value == "GROUPPOLICYCONTAINER" :
            cypher_key = "gpo.name"
            member_value = "*"
        elif member_value == "CONTAINER" :
            cypher_key = "container.name"
            member_value = "*"
        else:
            cypher_key = "n:" + member_value[0] + member_value[1:].lower()
            member_value = ""
    elif member_key == "memberof" :
        cypher_key = "toUpper(gC.name)"
    elif member_key == "member" :
        cypher_key = "toUpper(memberC.samaccountname)" 
    elif member_key == "serviceprincipalnames" :
        cypher_key = "ANY (spn IN n.serviceprincipalnames WHERE toUpper(spn)"
    elif member_key == "ou" :
        cypher_key = "toUpper(ou.name)"
    elif member_key == "gpo" :
        cypher_key = "toUpper(gpo.name)"
    elif member_key == "container" :
        cypher_key = "toUpper(container.name)"
    else:
        if("-" in member_key):
            cypher_key = "toUpper(n.`{key}`)".format(key=member_key)
        else:
            cypher_key = "toUpper(n.{key})".format(key=member_key)

    if member_value == "TRUE" or member_value == "FALSE" :
        cypher_key = "n.{key}".format(key=member_key)
        member_value = member_value[0] + member_value[1:].lower()

    return cypher_key, member_value

def adapt_attribute_to_cypher(member_key) -> str:
    member_key = member_key.lower()

    if member_key == "cn" :
        cypher_key = "n.name"
    elif member_key == "memberof" :
        cypher_key = "collect('memberOf: ' + g.name) AS memberof"
    elif member_key == "member" :
        cypher_key = "collect('member : ' + member.name) as member"
    elif member_key == "serviceprincipalnames" :
        cypher_key = "collect('serviceprincipalnames : ' + n.serviceprincipalnames) as serviceprincipalnames"
    else:
        if("-" in member_key):
            cypher_key = "n.`{key}`".format(key=member_key)
        else:    
            cypher_key = "n.{key}".format(key=member_key)
    
    return cypher_key
    
def compute_comparation(member_key, comparator, member_value) -> tuple:
    if "n:" in member_key : # n:Group, n:Computer...
        return "",""
    else:
        if "*" in member_value : 
            member_value_raw = member_value.strip("'")
            cypher_comparator, cypher_value = "", ""

            if member_value_raw[0] == "*" and member_value_raw[-1] == "*" :
                cypher_comparator = " CONTAINS "
                cypher_value = "'{value}'".format(value=member_value_raw[1:-1])
            elif member_value_raw[0] != "*" and member_value_raw[-1] == "*" :
                cypher_comparator = " STARTS WITH " 
                cypher_value = "'{value}'".format(value=member_value_raw[0:-1])
            elif member_value_raw[0] == "*" and member_value_raw[-1] != "*" :
                cypher_comparator = " ENDS WITH "
                cypher_value = "'{value}'".format(value=member_value_raw[1:])
            
            return cypher_comparator, cypher_value
        if member_key == "gC.name" :
            return " STARTS WITH ", "'{value}'".format(value=member_value_raw)
        
        return " {comparator} ".format(comparator = comparator), member_value

def tokenize_ldap_to_cypher(tokenized_operator, tokenized_items) -> str:
    if tokenized_operator == None :
        itemList = re.split(r"(<=|>=|=|>|<)", tokenized_items[0])

        token_key, token_value = adapt_ldap_item_to_cypher(itemList[0], itemList[2])

        if token_value != "True" and token_value != "False" :
            token_value = "'{value}'".format(value=token_value)

        comparation, token_value = compute_comparation(token_key, itemList[1], token_value)

        if "n.serviceprincipalnames" in token_key :
            return "{key}{comparation}{value})".format(key=token_key, comparation=comparation, value=token_value)
        else:
            return "{key}{comparation}{value}".format(key=token_key, comparation=comparation, value=token_value)
    else:
        expressions = []

        for item in tokenized_items:
            item_operator, item_items = item

            expressions.append(tokenize_ldap_to_cypher(item_operator, item_items))

        #Special rules on AND
        if tokenized_operator == '&' :
            # Multiple memberOf / member in an AND        
            memberof_count, member_count = 0, 0
            memberof_expressions, member_expressions = [], []

            # Query OU info (&(objectClass=OrganizationalUnit)(cn=whatever))
            is_ou_objectclass = False
            # Query GPO info (&(objectClass=GroupPolicyContainer)(cn=whatever))
            is_gpo_objectclass = False

            for index, expression in enumerate(expressions):
                if "gC.name" in expression:
                    memberof_count += 1
                    memberof_expressions.append((index,expression.replace("gC.name", f"g{index}.name")))
                if "memberC.samaccountname" in expression:
                    member_count += 1
                    member_expressions.append((index,expression.replace("memberC.samaccountname", f"member{index}.samaccountname")))
                
                match = re.search(r'\bou\.name\b', expression)
                if match and not expression[match.start() - 1] == '(':
                    is_ou_objectclass = True

                match = re.search(r'\bgpo\.name\b', expression)
                if match and not expression[match.start() - 1] == '(':
                    is_gpo_objectclass = True

                if is_ou_objectclass :
                    expressions[index] = expression.replace("n.", "ou.")
                elif is_gpo_objectclass :
                    expressions[index] = expression.replace("n.", "gpo.")

            if memberof_count > 1:
                for index, expression in memberof_expressions:
                    new_value = "EXISTS {{\n\tMATCH (n)-[:MemberOf]->(g{index}:Group)\n\tWHERE {expression}\n}}".format(index = index, expression = expression)
                    expressions[index] = new_value
            if member_count > 1 :
                for index, expression in member_expressions:
                    new_value = "EXISTS {{\n\tMATCH (n)<-[:MemberOf]-(member{index})\n\tWHERE {expression}\n}}".format(index = index, expression = expression)
                    expressions[index] = new_value

        # --      

        if tokenized_operator == '|':
            return "( " + " OR ".join(expressions) + " )"
        elif tokenized_operator == '&':
            return  "( " + " AND ".join(expressions) + " )" 
        elif tokenized_operator == "!":
            return " NOT ( " + expressions[0] + " )"

def tokenize_ldap_query(tokens) -> tuple:
    operator = None
    expressions = []

    while tokens:
        token = tokens.pop(0)
        
        if token == '(':
            expressions.append(tokenize_ldap_query(tokens))
        elif token == ')':
            return (operator, expressions)
        elif token in ('&', '|', '!'):
            operator = token
        else:
            expressions.append(token)

    return (operator, expressions)

def ldap_to_cypher(query) -> tuple:
    tokens = re.findall(r'([()|&!])|(\w+[><=~]*=?[^()|&!]+)', query)
    tokens = [item[0] or item[1] for item in tokens]

    push_debug_info("[•] Tokenized LDAP Query \n\n{msg}\n".format(msg = str(tokens)))

    tokenized_query = tokenize_ldap_query(tokens)[1]
    if "(" not in query and ")" not in query : 
        return tokenize_ldap_to_cypher(None, tokenized_query)
    else:
        return tokenize_ldap_to_cypher(tokenized_query[0][0], tokenized_query[0][1])


def create_cypher_query(query, attribute_list) -> str:
    where_clauses = ldap_to_cypher(query)
    query = query.lower().strip()

    # 1- MATCH
    cypher_query = "MATCH (n)"

    if re.search(r"\bou\b", query):
        cypher_query = "MATCH (ou:OU)-[:Contains]->(n)"
    if re.search(r"\bgpo\b", query):
        cypher_query = "MATCH (gpo:GPO)-[:GPLink]->(n)"
    if re.search(r"\bcontainer\b", query) :
        cypher_query = "MATCH (container:Container)-[:Contains]->(n)"

    if "organizationalunit" in query:
        cypher_query = "MATCH (ou:OU)"
    if "grouppolicycontainer" in query :
        cypher_query = "MATCH (gpo:GPO)"

        
    if re.search(r'\bmemberof\b', query) and re.search(r'\bmember\b', query):        
        cypher_query += "-[:MemberOf]->(gC:Group)<-[:MemberOf]-(memberC)\n"
    elif ("memberof" in query):
        cypher_query += "-[:MemberOf]->(gC:Group)\n"
    elif "member" in query :
        cypher_query += "<-[:MemberOf]-(memberC)\n"
    else:
        cypher_query += "\n"

    # 2- WHERE
    cypher_query += "WHERE {where_clauses}\n".format(where_clauses = where_clauses)    

    # 3- OPTIONAL MATCH
    if("organizationalunit" not in query and "grouppolicycontainer" not in query):
        cypher_query += "OPTIONAL MATCH (n)-[:MemberOf]->(g:Group)\nOPTIONAL MATCH (n)<-[:MemberOf]-(member)\n"

    # 4- WITH 
    if "grouppolicycontainer" in query : 
        cypher_query += "WITH gpo AS n, '' as memberof, '' as member\n"
    elif "organizationalunit" in query : 
        cypher_query += "WITH ou AS n, '' as memberof, '' as member\n"
    elif re.search(r'=\s*container', query) : 
        cypher_query += "WITH container AS n, '' as memberof, '' as member\n"
    
    elif attribute_list == None :
        cypher_query += "WITH n, collect('memberOf: ' + g.name) AS memberof, collect('member : ' + member.name) as member\n"

    # 5- RETURN
    attributes = ""
    if attribute_list :
        attributes_tmp = ""
        for attribute in attribute_list:
            attribute = adapt_attribute_to_cypher(attribute)
            attributes_tmp += "{attr}, ".format(attr = attribute)
        
        attributes += attributes_tmp[:-2]
    else:
        attributes = "n, memberof, member"

    cypher_query += "RETURN DISTINCT {attributes}".format(attributes = attributes)

    return cypher_query


# -- OUTPUT FORMATING FUNCTIONS --
def format_spn(remaining_attrs) -> str:
    ldap_output = ""
    if remaining_attrs != [] :
        for principal in remaining_attrs:
            ldap_output += "serviceprincipalnames: " +  principal + "\n"

    return ldap_output

def format_membership_list(remaining_attrs) -> str:
    ldap_output = ""

    for group in set(remaining_attrs):
        ldap_output += group + "\n"
    
    return ldap_output

def format_others_output(remaining_attrs) -> str:
    ignore_list = ["owned", "sensitive", "lastlogon"]

    ldap_output = ""
    for attribute in remaining_attrs:
        if attribute not in ignore_list :
            ldap_output += attribute + ": " + str(remaining_attrs[attribute]) + "\n"

    return ldap_output

def format_computer_output(remaining_attrs) -> tuple:
    computer_attrs_order = ["serviceprincipalnames", "dnshostname", "trustedtoauth", "unconstraineddelegation", "allowedtodelegate"]
    ldap_output = ""

    if "serviceprincipalnames" in remaining_attrs and "serviceprincipalname" in remaining_attrs :
        remaining_attrs.pop("serviceprincipalname")

    if "serviceprincipalnames" in remaining_attrs : #Computer
        for attribute in computer_attrs_order:
            if attribute == "serviceprincipalnames" :
                ldap_output += format_spn(remaining_attrs.pop("serviceprincipalnames"))
            else:
                if attribute in remaining_attrs :
                    ldap_output += attribute + ": " + str(remaining_attrs.pop(attribute)) + "\n"

    return remaining_attrs, ldap_output
    
def format_general_output(remaining_attrs) -> tuple:
    important_attrs_order = ["name", "samaccountname", "userprincipalname", "distinguishedname", "displayname", "title", "description", "objectid", "domain", "domainsid", "enabled", "useraccountcontrol", "highvalue"]
    date_attrs_order = ["whencreated", "lastlogontimestamp", "pwdlastset"]
    
    ldap_output = ""

    for attribute in important_attrs_order:
        if attribute in remaining_attrs :
            attribute_value = remaining_attrs.pop(attribute)
            if attribute_value :
                ldap_output += attribute + ": " + str(attribute_value) + "\n"

    ldap_output += format_membership_list(remaining_attrs.pop("memberof"))
    
    for attribute in date_attrs_order:
        if attribute in remaining_attrs :
            ldap_output += attribute + ": " + str(parse_timestamp(remaining_attrs.pop(attribute))) + "\n"

    ldap_output += format_membership_list(remaining_attrs.pop("member"))

    return remaining_attrs, ldap_output

# -- Format by attributes -- 
def format_special_attributes(attribute, remaining_attrs) -> str:
    special_attr_output = ""
    special_attributes = ["member", "memberof", "serviceprincipalnames"]

    if attribute == special_attributes[0] :
        special_attr_output += format_membership_list(remaining_attrs["member"])
    elif attribute == special_attributes[1] :
        special_attr_output += format_membership_list(remaining_attrs["memberof"])
    elif attribute == special_attributes[2] :
        special_attr_output += format_spn(remaining_attrs["serviceprincipalnames"][0][1:])

    return special_attr_output

def format_by_attributes(attribute, remaining_attrs) -> str:
    attr_output = ""

    special_attributes = ["member", "memberof", "serviceprincipalnames"]
    date_attributes = ["whencreated", "lastlogontimestamp", "pwdlastset"]

    if attribute in special_attributes :
        attr_output += format_special_attributes(attribute, remaining_attrs)
    elif attribute  in date_attributes :
        item_key = adapt_attribute_to_cypher(attribute)
        attr_output += item_key.split(".")[1] + ": " + str(parse_timestamp(remaining_attrs.pop(item_key))) + "\n"
    else:
        item_key = adapt_attribute_to_cypher(attribute)
        if item_key in remaining_attrs :
            if("-" in item_key):
                attr_output += item_key.split(".")[1].strip("`") + ": " + str(remaining_attrs[item_key]) + "\n"
            else:      
                attr_output += item_key.split(".")[1] + ": " + str(remaining_attrs[item_key]) + "\n"

    return attr_output

# -- 
def push_debug_info(msg) -> None:
    controller = N4LController().get_instance()
    controller.push_debug_info(msg)
    
def parse_record(record, attributes, raw) -> str:
    remaining_attrs = {}
    ldap_output = ""

    for item_key, item_value in record.items():
        if item_key == "n" :
            for property_key, property_value in item_value.items():
                remaining_attrs[property_key] = property_value
        else:
            remaining_attrs[item_key] = item_value

    if "ntsecuritydescriptor" in remaining_attrs :
        remaining_attrs.pop("ntsecuritydescriptor")

    if attributes :
        for attribute in attributes:
            attribute = attribute.lower()
            ldap_output += format_by_attributes(attribute, remaining_attrs)
    else:
        remaining_attrs, ldap_output_tmp = format_general_output(remaining_attrs)
        ldap_output += ldap_output_tmp

        remaining_attrs, ldap_output_tmp = format_computer_output(remaining_attrs)
        ldap_output += ldap_output_tmp

        if raw :
            ldap_output += format_others_output(remaining_attrs)

    return ldap_output

def execute_query(query, attributes, raw) -> str:
    with Neo4jConnector.driver.session(database=Neo4jConnector.database) as session:
        try:
            result = session.run(query)
        except:
            controller = N4LController().get_instance()
            controller.notify_error(traceback.format_exc())

        ldap_output = ""
 
        has_data = False
        for record in result:
            has_data = True
            ldap_output += parse_record(record, attributes, raw)
            ldap_output += "\n\n"

        if not has_data :
            ldap_output = "No data found"

        return ldap_output

def perform_query(query, attributes, raw) -> None:    
    controller = N4LController().get_instance()

    try:
        push_debug_info("[•] LDAP\n\n{msg}\n".format(msg = query))

        cypher_query = create_cypher_query(query, attributes)
        push_debug_info("[•] Cypher\n\n{msg}\n".format(msg = cypher_query))

        ldap_output = execute_query(cypher_query, attributes, raw)
        push_debug_info("[✓] Query executed")

        if ldap_output != "No data found" :
            controller.redraw_LDAP_result_table(ldap_output)
        else:
            controller.notify_no_results("LDAP Query didn't return any result")
        
    except:
        controller.notify_error(traceback.format_exc())