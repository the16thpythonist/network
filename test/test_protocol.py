import network.protocol as protocol
import unittest
import socket
import random
import threading
import json
import time


def open_port():
    """
    This function will return an open network port
    Returns:
    the integer port number of the open port
    """
    # Choosing the port random in the upper port range
    port = random.randint(30000, 60000)
    result = 0
    while result == 0:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        address = ('127.0.0.1', port)
        # attempting to connect to the server, in case not possible, there is no socket on the port -> port is free
        result = sock.connect_ex(address)
        port = random.randint(30000, 60000)
    # Returning the found free port
    return port


class TestForm(unittest.TestCase):

    std_title = "Test"
    std_body = "this is just a short body\nWith two rows\n"
    std_appendix = ["one", "two"]

    def test_init(self):
        # Building the form
        form = protocol.Form(self.std_title, self.std_body, self.std_appendix)
        self.assertEqual(form.title, self.std_title)
        self.assertEqual(form.body, self.std_body)
        self.assertEqual(form.appendix, self.std_appendix)

    def test_body(self):
        # Testing the turing of a list into a line separated string
        body_list = ["first line", "second line", "third line"]
        body_string = "first line\nsecond line\nthird line"
        form = protocol.Form(self.std_title, body_list, self.std_appendix)
        self.assertEqual(form.body, body_string)
        # Testing using other data types in the list to be the body
        body_list = [10, 11, 12]
        body_string = "10\n11\n12"
        form = protocol.Form(self.std_title, body_list, self.std_appendix)
        self.assertEqual(form.body, body_string)
        # Testing for having a really long list
        body_list = list(range(1, 10000, 1))
        body_string = '\n'.join(map(str, body_list))
        form = protocol.Form(self.std_title, body_list, self.std_appendix)
        self.assertEqual(form.body, body_string)

    def test_init_error(self):
        # Testing if the correct exceptions are risen in case a wrong param is passed
        with self.assertRaises(TypeError):
            protocol.Form(12, self.std_body, self.std_appendix)
        with self.assertRaises(ValueError):
            protocol.Form(self.std_title, 12, self.std_appendix)
        with self.assertRaises(ValueError):
            protocol.Form(self.std_title, self.std_body, "{hallo")

    def test_appendix(self):
        # Testing the turning of a list into a json string by the form
        appendix_dict = {"a": ["first", 129], "b": list(map(str, [1, 2, 3]))}
        appendix_json = json.dumps(appendix_dict)
        form = protocol.Form(self.std_title, self.std_body, appendix_dict)
        self.assertEqual(form.appendix_json, appendix_json)
        # Testing if the json string gets detected as such and loaded from the json format
        form = protocol.Form(self.std_title, self.std_body, appendix_json)
        self.assertDictEqual(form.appendix, appendix_dict)
        # Testing in case of a very long data structure
        # Creating a very long dictionary structure
        long_dict = {}
        for i in range(1, 1000, 1):
            sub_dict = {}
            for k in range(1, 100, 1):
                sub_dict[str(k)] = ["random", "random", "random"]
            long_dict[str(i)] = sub_dict
        long_json = json.dumps(long_dict)
        # Testing the internal conversion from dict to json
        form = protocol.Form(self.std_title, self.std_body, long_dict)
        self.assertEqual(form.appendix_json, long_json)
        # Testing the internal conversion from json string to object
        form = protocol.Form(self.std_title, self.std_body, long_json)
        self.assertDictEqual(form.appendix, long_dict)

    def test_empty(self):
        # Testing in case an empty object is given as appendix
        form = protocol.Form('', '', [])
        self.assertTrue(form.empty)
        # Testing in case an empty string is given as appendix
        form = protocol.Form('', '', '')
        self.assertTrue(form.empty)
        # Testing in case the body is an empty list
        form = protocol.Form('', [], '')
        self.assertTrue(form)

    def test_valid(self):
        # Checking if the valid property is actually false with empty title
        form = protocol.Form('', self.std_body, self.std_appendix)
        self.assertFalse(form.valid)
        # A form should also be unvalid in case it is empty
        form = protocol.Form(self.std_title, '', '')
        self.assertFalse(form.valid)
        self.assertTrue(form.empty)


class SockGrab(threading.Thread):
    """
    This is a utility class, which will open a server socket at the given port and then simply wait for the first
    incoming connection and then assign the bound socket, which is the result of this first established connection to
    the internal 'connection' attribute, where it can be grabbed for further use.
    """
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = ('127.0.0.1', port)
        self.connector = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection = None

    def run(self):
        """
        The main method of the Thread, which will be called after the Thread was started. This will simply define the
        internal socket object as a server and wait for a connection, which it then assigns to the connection attribute
        Returns:
        void
        """
        self.sock.bind(self.address)
        self.sock.listen(2)
        self.connection, address = self.sock.accept()

    def sockets(self):
        """
        This method returns the pair of connected sockets.
        Returns:
        The
        """
        # Connecting the connector
        self.connect()
        # Waiting for the corresponding socket was accepted in the server socket
        self.get_connection()
        return self.connection, self.connector

    def get_connection(self):
        """
        This method is used to get the connected server socket from the Thread. The method will be blocking until the
        connection attribute is assigned the connected socket from the server accepting or the timeout of waiting one
        second has been exceeded
        Raises:
            TimeoutError: In case, that even one second after the method was called, the socket was sill not assigned
                to the connection attribute of this object
        Returns:
        The socket object, that was given by the server for the established connection
        """
        start_time = time.time()
        while self.connection is None:
            delta = time.time() - start_time
            if delta > 1:
                raise TimeoutError("Connection problems in testing")
        return self.connection

    def connect(self):
        """
        This method will simply connect the internal connector socket to the server. Thus it has to be called only
        after the Thread has been started
        Returns:
        void
        """
        self.connector.connect(self.address)


class TestFormTransmission(unittest.TestCase):

    std_separation = "$separation$"
    std_port = 56777

    def test_init(self):
        port = open_port()
        s = SockGrab(port)
        s.start()
        print(s.sockets())

    def socket_pair(self):
        pass

