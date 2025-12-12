from math import ceil, sqrt
from message import Message, MessageType
from nodeServer import NodeServer
from nodeSend import NodeSend
from queue import PriorityQueue
from threading import Thread, Condition
import config
import random
import time


class Node(Thread):
    """
    Represents a Node of the distributed system.

    Attributes:
        id (int): Node's identifier.
        port (int): Node's port.
        daemon (bool): Thread's daemon option.
        lamport_ts (int): Lamport timestamp of the last message sent.
        server (NodeServer): Server for handling the incoming messages.
        client (NodeSend): Client for handling message sending.
        colleagues (list): List of colleagues in the Node's quorum.
        condition (Condition): Condition upon which entering the CS is allowed
        queue (PriorityQueue): Stores other nodes' requests based on priority.
        grants_sent (tuple): Highest priority node to which a GRANT is sent.
        grants_received (set): IDs of the nodes that have conceded a GRANT.
        yielded (bool): True if the node has already yielded; False otherwise.
        failed (bool): True if the node has received a FAILED; False otherwise.
        in_CS (bool): True if the node is in the critical section; False otherwise.
    """

    _FINISHED_NODES = 0
    _HAVE_ALL_FINISHED = Condition()

    def __init__(self, id):
        """Constructor for class Node."""
        Thread.__init__(self)
        self.id = id
        self.port = config.port+id
        self.daemon = True
        self.lamport_ts = 0
        self.__form_colleagues()
        self.server = NodeServer(self)
        self.server.start()
        self.client = NodeSend(self)
        self.condition = Condition()
        self.queue = PriorityQueue()
        self.grants_sent = None
        self.grants_received = set()
        self.yielded = False
        self.failed = False
        self.in_CS = False


    def do_connections(self):
        """Connects to all nodes via socket."""
        self.client.build_connection()


    def __form_colleagues(self):
        """
        Forms the quorum for the Node placing all nodes in a matrix of √N x √N,
        selecting the ones in the same row and column.
        """
        num_rows = ceil(sqrt(config.numNodes))
        row_index = self.id // num_rows
        col_index = self.id % num_rows

        colleagues = set()

        for j in range(num_rows):
            pos = row_index * num_rows + j
            if pos >= config.numNodes:
                break
            colleagues.add(pos)

        for i in range(num_rows):
            pos = i * num_rows + col_index
            if pos >= config.numNodes:
                continue
            colleagues.add(pos)

        while len(colleagues) < (2 * num_rows - 1):
            colleagues.add(random.randint(0, config.numNodes-1))

        colleagues.discard(self.id)
        self.colleagues = list(colleagues)


    def run(self):
        """Main thread loop that performs Maekawa mutual-exclusion actions."""
        print(f"Run Node{self.id} with the follows {self.colleagues}")
        self.client.start()

        self.wakeupcounter = 0
        while self.wakeupcounter <= 2: # Termination criteria
            # Nodes with different starting times
            time_offset = random.uniform(2, 8)
            time.sleep(time_offset)

            # Send requests to all quorum peers
            self.grants_received.add(self.id)

            req = Message(
                msg_type=MessageType.REQUEST,
                src=self.id,
                ts=self.lamport_ts,
            )
            self.client.multicast(req, self.colleagues)
            print(f"Node_{self.id} sent {req.msg_type} to {self.colleagues}")

            # Wait for a unanimous grant
            with self.condition:
                while len(self.grants_received) < len(self.colleagues):
                    self.condition.wait()

                self.in_CS = True

            # ENTER CRITICAL SECTION
            print(f"[Node_{self.id}]: Greetings from the critical section!")
            time_offset = random.uniform(0.5, 1.5)
            time.sleep(time_offset)
            # EXIT CRITICAL SECTION

            with self.condition:
                self.grants_received.clear()
                self.in_CS = False

            # Send release messages to all quorum peers
            rel = Message(
                msg_type=MessageType.RELEASE,
                src=self.id,
                ts=self.lamport_ts,
            )
            self.client.multicast(rel, self.colleagues)
            print(f"Node_{self.id} sent {req.msg_type} to {self.colleagues}")

            # Control iteration
            self.wakeupcounter += 1

        # Wait for all nodes to finish
        print(f"Node_{self.id} is waiting for all nodes to finish")
        self._finished()

        print(f"Node_{self.id} DONE!")


    @staticmethod
    def _finished():
        """
        Increments the counter of finished nodes and blocks until all nodes have called this method.
        Notifies all waiting threads once the last node reaches the barrier.
        """
        with Node._HAVE_ALL_FINISHED:
            Node._FINISHED_NODES += 1
            if Node._FINISHED_NODES == config.numNodes:
                Node._HAVE_ALL_FINISHED.notify_all()

            while Node._FINISHED_NODES < config.numNodes:
                Node._HAVE_ALL_FINISHED.wait()


    def request_handler(self, msg: Message):
        """
        Process a request from a peer.

        Behavior:
            - If this node hasn't granted to anyone, send GRANT to the requester.
            - If this node has granted to a higher-priority request, enqueue the incoming request and reply with FAILED.
            - If this node has granted to a lower-priority request, enqueue the incoming request and send INQUIRE
                to the node that currently holds the GRANT so it can decide whether to yield.
        """
        # Get the highest priority node that has received a GRANT from this
        if self.grants_sent:
            hp_ts, hp_src = self.grants_sent

            if (hp_ts, hp_src) < (msg.ts, msg.src):
                rep = Message(
                    MessageType.FAILED,
                    self.id,
                    msg.src,
                    self.lamport_ts,
                )
                self.client.send_message(rep, msg.src)
                self.queue.put((msg.ts, msg.src))

                print(f"Node_{self.id} sent msg: {rep.msg_type}")

            else:
                rep = Message(
                    MessageType.INQUIRE,
                    self.id,
                    hp_src,
                    self.lamport_ts,
                    (msg.ts, msg.src),
                )
                self.client.send_message(rep, hp_src)
                self.queue.put((msg.ts, msg.src))

                print(f"Node_{self.id} sent msg: {rep.msg_type}")

        # Reply with a GRANT if no other GRANTs have been sent.
        else:
            rep = Message(
                MessageType.GRANT,
                self.id,
                msg.src,
                self.lamport_ts,
            )
            self.client.send_message(rep, msg.src)
            self.grants_sent = (msg.ts, msg.src)

            print(f"Node_{self.id} sent msg: {rep.msg_type}")


    def yield_handler(self, msg: Message):
        """Enqueues the yielding request and grant the next one."""
        # Put the yielding node in the queue
        self.queue.put((msg.ts, msg.src))

        # Clear the grant sent to the yielding node
        if self.grants_sent and (msg.ts, msg.src) == self.grants_sent:
            self.grants_sent = None

        # Get the info of the highest priority request in the queue
        if not self.queue.empty():
            q_ts, q_src = self.queue.get()

            rep = Message(
                MessageType.GRANT,
                self.id,
                q_src,
                self.lamport_ts,
            )
            self.client.send_message(rep, q_src)
            self.grants_sent = (q_ts, q_src)

            print(f"Node_{self.id} sent msg: {rep.msg_type}")


    def release_handler(self, msg: Message):
        """
        Removes the releasing node from any local queue or grants state and,
        if there are waiting requests, grants the highest-priority one.
        """
        # Remove the releasing node from the queue and grants_sent
        if self.grants_sent and (msg.ts, msg.src) == self.grants_sent:
            self.grants_sent = None

        new_queue = PriorityQueue()
        while not self.queue.empty():
            q_ts, q_src = self.queue.get()
            if q_src == msg.src:
                continue
            new_queue.put((q_ts, q_src))
        self.queue = new_queue

        # Sent a GRANT to the request with the highest priority
        if not self.queue.empty():
            q_ts, q_src = self.queue.get()

            rep = Message(
                MessageType.GRANT,
                self.id,
                q_src,
                self.lamport_ts,
            )
            self.client.send_message(rep, q_src)
            self.grants_sent = (q_ts, q_src)

            print(f"Node_{self.id} sent msg: {rep.msg_type}")

        else:
            self.grants_sent = None


    def inquire_handler(self, msg: Message):
        """
        If this node is not currently in the critical section, it responds with a YIELD, so the inquiring node
        can reassign its grants; otherwise the INQUIRE is ignored (the node keeps its grant).
        """
        rep = None

        # If it hasn't got the CS, yield
        with self.condition:
            if not self.in_CS:
                rep = Message(
                    MessageType.YIELD,
                    self.id,
                    msg.src,
                    self.lamport_ts,
                )

                self.yielded = True
                if msg.src in self.grants_received:
                    self.grants_received.remove(msg.src)

        # Send a yield message if created
        if rep:
            self.client.send_message(rep, msg.src)
            print(f"Node_{self.id} sent msg: {rep.msg_type}")


    def grant_handler(self, msg: Message):
        """
        Adds the granting node to the received's list, resets the flags, and notifies the local condition variable
        if the node has collected grants from a full quorum.
        """
        with self.condition:
            self.grants_received.add(msg.src)
            self.yielded = False
            self.failed = False

            if not len(self.grants_received) < len(self.colleagues):
                self.condition.notify()


    def failed_handler(self):
        """
        Marks the local state to indicate the current request was denied by at least one peer.
        """
        with self.condition:
            self.failed = True
            self.yielded = True
