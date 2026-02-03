## About Neo4LDAP

**Neo4LDAP** is a query and visualization tool focused on **Active Directory**. It combines LDAP syntax with graph-based data analysis in Neo4j, offering an alternative approach to tools like BloodHound.

<img width="1916" height="930" alt="Image" src="https://github.com/user-attachments/assets/40624370-29e1-4523-bc84-90bcdd5e4ebb" />

<img width="1914" height="928" alt="Image" src="https://github.com/user-attachments/assets/8e709694-aa4c-486a-9037-dfe628637b85" />

---

## Capabilities

### LDAP Viewer

- Run **complex and expressive queries** directly against Neo4j  
- **No need to learn Cypher**: queries can be written in **LDAP syntax**  
- Create **custom reusable queries**
- **Owned nodes** are highlighted to improve visibility and search efficiency

### Graph Viewer

- Analyze Active Directory ACLs through **interactive graphs**.
    - Outbound analysis
    - Inbound analysis
    - Targeted analysis 
- Advanced techniques to **reduce visual noise**
    - **Exclude nodes** to remove irrelevant elements from the view
    - **Temporarily hide graph sections** to improve focus and readability
    - **Depth-limited search** to control graph size and prevent visual clutter
- Full control over **graph behavior**
    - Define the relevance of each ACE to match your objectives
    - **Context-driven algorithms** that adapt to your analytical needs

### Integration with BloodHound Workflows

- Neo4LDAP can **ingest data from BloodHound JSON files**  
- Support for both **Legacy** and **Community Edition (CE)** formats
- **Fast, multithreaded** ingestion

### Other capabilities

- **Multi-database** support
- **Independent panels**: analyze graphs while querying data simultaneously, without losing context 

--- 

> 📘 To maximize the effectiveness of Neo4LDAP and gain a deeper understanding of how it handles special cases and internal logic, it is highly recommended to read through the full [project wiki](https://github.com/Krypteria/Neo4LDAP/wiki). The documentation covers key design decisions, usage examples, and query behaviors that may not be immediately apparent.

Additionally, there are **two articles** covering the tool's internals:
- [Goodbye Cypher, Hello LDAP: Querying Neo4j with Neo4LDAP](https://medium.com/@kripteria.sec/goodbye-cypher-hello-ldap-querying-neo4j-with-neo4ldap-5e6466426a01)
- [Finding optimal attack paths in Active Directory with Neo4LDAP](https://medium.com/@kripteria.sec/finding-optimal-attack-paths-in-active-directory-with-neo4ldap-3d2158419f35)

--- 

# Recommendations

Ingestion of large JSONs may affect memory efficiency. If you have a large JSON file, it is advisable to split it into chunks using [ShredHound](https://github.com/ustayready/ShredHound) before uploading them.

You can modify the scale factor of Neo4LDAP by using the following command:
```bash
QT_SCALE_FACTOR=<VALUE> neo4ldap
```
# Installation

Neo4LDAP uses **Neo4j** as its database. To use the tool, you must install and run a Neo4j instance. For installation instructions, please refer to the [official Neo4j installation guide](https://neo4j.com/docs/operations-manual/2025.08/installation/)

Once Neo4j is installed, start it by running:
```bash
neo4j console
```

To install **Neo4LDAP**, it is recommended to use a **Conda virtual environment** with **Python 3.9.13 or higher** to isolate the installation and avoid dependency conflicts:

```bash
conda create -n neo4ldap python=3.9.13
conda activate neo4ldap
```

Once the conda environment is activated, install the following **Python dependencies** using `pip`:

```bash
pip install networkx neo4j-rust-ext PySide6
```

Depending on the display server protocol you are using, you must install **some extra dependencies**. To check which display server protocol you are using, execute the following command:
```bash
echo $XDG_SESSION_TYPE
```

If that command returns ```x11```, you must install the following **dependency**:
```bash
sudo apt install libxcb-cursor0
```

It is recommended to define the following **shell alias** in .bashrc, .zshrc, or equivalent shell configuration:

```bash
nano ~/.bashrc

neo4ldap() {
    cd <installation path> || return
    python -m Neo4LDAP.Neo4LDAP
}

source ~/.bashrc
```

# Acknowledgements

Special thanks to [@_wald0](https://twitter.com/_wald0), [@CptJesus](https://twitter.com/CptJesus), and [@harmj0y](https://twitter.com/harmj0y) for their work on **BloodHound**, a tool that has served as a foundational reference and source of inspiration for the development of Neo4LDAP.
