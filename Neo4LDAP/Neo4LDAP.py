from Neo4LDAP.model.N4L_Common import *
from Neo4LDAP.controllers.N4L_Controller import N4LController

def Neo4LDAP() -> None:
    controller = N4LController().get_instance()
    controller.init_gui()

if __name__ == "__main__":
    Neo4LDAP()
