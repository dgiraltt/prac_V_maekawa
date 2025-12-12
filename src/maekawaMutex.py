from node import Node
import config


class MaekawaMutex(object):
    """
    Initializes and runs a Maekawa mutual exclusion algorithm.

    Attributes:
        nodes (list): List of Nodes representing the distributed nodes.
    """

    def __init__(self):
        self.nodes =[Node(i) for i in range(config.numNodes)]


    def define_connections(self):
        """Defines the connections between each node and all others."""
        for node in self.nodes:
            node.do_connections()


    def run(self):
        """Starts all the nodes and waits for them all to finish."""
        self.define_connections()
        for node in self.nodes:
            node.start()

        for node in self.nodes:
            node.join()
