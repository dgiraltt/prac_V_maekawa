from message import Message, MessageType
from threading import Thread
import json
import select
import utils


class NodeServer(Thread):
    """
    Handles the messages received by the nodes to responde them.

    Attributes:
        node (Node): Node that receives the messages as a server.
        daemon (bool): Thread's daemon option.
        connection_list(list): Stores all connections to this node as a server.
        server_socket(socket.socket): Socket as server.
    """

    def __init__(self, node):
        Thread.__init__(self)
        self.node = node
        self.daemon = True


    def run(self):
        """Starts the objects of this class as Threads."""
        self.update()


    def update(self):
        """
        Handles the receiving of messages. Parses the stream of bytes to detect the different JSONs,
        converting them back into Messages to be processed.
        """
        self.connection_list = []
        self.server_socket = utils.create_server_socket(self.node.port)
        self.connection_list.append(self.server_socket)

        while self.node.daemon:
            (read_sockets, write_sockets, error_sockets) = select.select(
                self.connection_list, [], [], 20)
            if not (read_sockets or write_sockets or error_sockets):
                print(f'Node_{self.node.id} - Timed out') #force to assert the while condition
            else:
                for read_socket in read_sockets:
                    if read_socket == self.server_socket:
                        (conn, addr) = read_socket.accept()
                        self.connection_list.append(conn)
                    else:
                        try:
                            msg_stream, _ = read_socket.recvfrom(4096)
                            try:
                                msgs = Message.parse(str(msg_stream, "utf-8"))
                                for m in msgs:
                                    self.process_message(Message.from_json(json.loads(m)))
                            except Exception as e:
                                print("Exception: ", end="")
                                print(e)
                        except:
                            read_socket.close()
                            self.connection_list.remove(read_socket)
                            continue

        self.server_socket.close()


    def process_message(self, msg: Message):
        """
        Handles the type of message received.

        Raises:
            ValueError: If the type of the Message is not valid.
        """
        msg_type = msg.msg_type
        print(f"\tNode_{self.node.id} received {msg_type} from Node_{msg.src}")

        self.node.lamport_ts = max(self.node.lamport_ts, msg.ts) + 1
        match msg_type:
            case MessageType.REQUEST:
                self.node.request_handler(msg)
            case MessageType.YIELD:
                self.node.yield_handler(msg)
            case MessageType.RELEASE:
                self.node.release_handler(msg)
            case MessageType.INQUIRE:
                self.node.inquire_handler(msg)
            case MessageType.GRANT:
                self.node.grant_handler(msg)
            case MessageType.FAILED:
                self.node.failed_handler()
            case _:
                raise ValueError(f"[ValueError]: Unknown message type: {msg_type}")
