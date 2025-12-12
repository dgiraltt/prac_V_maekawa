from copy import deepcopy
from threading import Thread
import config
import utils


class NodeSend(Thread):
    """Handles a node's operations related to message sending."""

    def __init__(self, node):
        Thread.__init__(self)
        self.node = node
        self.client_sockets = [utils.create_client_socket() for _ in range(config.numNodes)]


    def build_connection(self):
        """Connects each node client socket to the host and port."""
        for i in range(config.numNodes):
            self.client_sockets[i].connect(('localhost',config.port+i))


    def send_message(self, msg, dest, multicast=False):
        """
        Sends a message to one destination.

        Args:
            msg (Message): Message to be sent.
            dest (int): Destination Node id.
            multicast (bool, optional): True for a multicast option, False for a single destination.
        """
        if not multicast:
            self.node.lamport_ts += 1
            msg.set_ts(self.node.lamport_ts)
        assert dest == msg.dest
        self.client_sockets[dest].sendall(bytes(msg.to_json(),encoding='utf-8'))


    def multicast(self, msg, group):
        """
        Sends a message to all the Nodes of a set group.

        Args:
            msg (Message): Message to be sent.
            group (list): IDs of the nodes in the group.
        """
        self.node.lamport_ts += 1
        msg.set_ts(self.node.lamport_ts)
        for dest in group:
            new_msg = deepcopy(msg)
            new_msg.set_dest(dest)
            assert new_msg.dest == dest
            assert new_msg.ts == msg.ts
            self.send_message(new_msg, dest, True)
