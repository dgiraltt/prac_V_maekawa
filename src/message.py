import json


class MessageType:
    """Message types necessary."""
    REQUEST = "REQUEST"
    GRANT = "GRANT"
    RELEASE = "RELEASE"
    FAILED = "FAILED"
    INQUIRE = "INQUIRE"
    YIELD = "YIELD"


class Message(object):
    """
    Message sent between nodes.

    Attributes:
        msg_type (Message_Type): Type of the message.
        src (int): ID of the message sender.
        dest (int): ID of the message receiver.
        ts (int): Lamport timestamp of the message sending.
        data (any, optional): Content of the message.
    """

    def __init__(self,
                 msg_type=None,
                 src=None,
                 dest=None,
                 ts=None,
                 data=None):
        self.msg_type = msg_type
        self.src = src
        self.dest = dest
        self.ts = ts
        self.data = data

    def set_type(self, msg_type):
        self.msg_type = msg_type

    def set_src(self, src):
        self.src = src

    def set_dest(self, dest):
        self.dest = dest

    def set_ts(self, ts):
        self.ts = ts

    def set_data(self, data):
        self.data = data


    def __json__(self):
        """Puts the Message in a JSON format."""
        return dict(msg_type=self.msg_type,
                    src=self.src,
                    dest=self.dest,
                    ts=self.ts,
                    data=self.data)


    def to_json(self):
        """Serializes the JSON representation of the Message."""
        obj_dict = dict()
        obj_dict['msg_type'] = self.msg_type
        obj_dict['src'] = self.src
        obj_dict['dest'] = self.dest
        obj_dict['ts'] = self.ts
        obj_dict['data'] = self.data
        return json.dumps(obj_dict)


    @staticmethod
    def from_json(msg):
        """
        Converts a JSON back into a Message.

        Args:
            msg (dict): JSONified Message.
        """
        return Message(
            msg_type=msg['msg_type'],
            src=msg['src'],
            dest=msg['dest'],
            ts=msg['ts'],
            data=msg['data']
        )


    @staticmethod
    def parse(str):
        """
        Parses a serialized JSONified Message to identify possible joined
        back-to-back JSONs. In case of finding any, it splits them in single
        serialized JSONs.

        Args:
            str (str): Serialized stream with one or more JSONs.

        Raises:
            ValueError: If some JSON does not end in '}'.

        Returns:
            list: All the serialized JSONs separated.
        """
        msgs = []

        while True:
            split = str.find("}{")
            if split == -1:
                if str[-1] != '}':
                    raise ValueError("JSON must end in }")
                msgs.append(str)
                break
            
            if str[:split + 1][-1] != '}':
                raise ValueError("JSON must end in }")
            msgs.append(str[:split + 1])
            str = str[split + 1:]

        return msgs
