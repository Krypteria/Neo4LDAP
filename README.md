## About Neo4LDAP

**Neo4LDAP** is a query and visualization tool focused on **Active Directory environments**. It combines LDAP syntax with graph-based data analysis in Neo4j, offering an alternative approach to tools like BloodHound.

---

### 🔍 LDAP-Driven Query Engine

Neo4LDAP translates LDAP queries into Cypher internally, allowing users to:

- Run **complex and expressive queries** directly against Neo4j  
- **Avoid learning Cypher**, using familiar LDAP syntax  
- **Quickly create custom queries** and extract relevant information  

---

### 🗺️ Graph Visualization for AD Structures

Neo4LDAP provides a graph interface designed to support **large and complex directory environments**, offering:

- **Exclude nodes** to eliminate irrelevant elements
- **Temporary hide parts of the graph** to improve visibility and focus
- **Depth-limited search** to control graph size and reduce visual clutter

These features improve clarity when analyzing access paths, ACLs, and privilege escalation scenarios.

---

### 🔗 Integration with BloodHound Workflows

To support existing ecosystems, Neo4LDAP includes:

- A **data ingestion feature** for importing BloodHound JSON files  
- Support for both **Legacy** and **Community Edition (CE)** formats  

This allows Neo4LDAP to **coexist with BloodHound** and be used as a practical alternative in the Active Directory cybersecurity field.

> ⚠️ **Disclaimer:** At the moment, only on-premise data is processed, Azure data is not currectly supported.


> 📘 To maximize the effectiveness of Neo4LDAP and gain a deeper understanding of how it handles special cases and internal logic, it is highly recommended to read through the full [project wiki](). The documentation covers key design decisions, usage examples, and query behaviors that may not be immediately apparent.

# Installation

It is recommended to use a Conda virtual environment with Python 3.9.13 or higher to isolate the installation and avoid dependency conflicts:

```bash
conda create -n neo4ldap python=3.9.13
conda activate neo4ldap
```

To install Neo4LDAP, install the following Python dependencies within the conda environment using `pip`:

```bash
pip install networkx neo4j PySide6
```

It is recommended to define the following shell alias in .bashrc, .zshrc, or equivalent shell configuration:

```bash
nano ~/.bashrc

neo4ldap() {
    cd <installation path> || return
    python -m Neo4LDAP.Neo4LDAP
}

source ~/.bashrc
```

# Demo

# Acknowledgements

Special thanks to [@_wald0](https://twitter.com/_wald0), [@CptJesus](https://twitter.com/CptJesus), and [@harmj0y](https://twitter.com/harmj0y) for their work on **BloodHound**, a tool that has served as a foundational reference and source of inspiration for the development of Neo4LDAP.
