import threading
import socket
import pickle
import time
import json

# UNIVERSAL


class SocketWrapper:
    """
    GENERAL
    This object wraps a socket connection and adds some additional functionality. A wrapped socket will be able to
    receive data until a certain character is received, only receive a certain length
    """
    def __init__(self, sock, connected):
        # Assigning the socket object to the variable
        self.sock = sock
        # The variable, which stores the state of the connection
        self.connected = connected
        # The properties, that describe the type of the socket
        self.family = None
        self.appoint_family()
        self.type = None
        self.appoint_type()

    def connect(self, ip, port, attempts, delay):
        """
        This method capsules the connect functionality of the wrapped socket. The method will try to connect to the
        specified address, trying that the specified amount of attempts.
        In case an already connected socket is already stored in the wrapper, this method will close and connect to the
        new address (in case that is possible obviously).
        In case the connection could not be established after the specified amount of attempts, the method will raise
        an ConnectionRefusedError!
        Args:
            ip: The string ip address of the target to connect to
            port: The integer port of the target to connect to
            attempts: The integer amount of attempts of trying to connect
            delay: The float amount of seconds delayed to the next attempt

        Returns:
        void
        """
        # Checking the data types for the inputs
        assert isinstance(ip, str), "ip is not a string"
        assert isinstance(port, int) and (0 <= port <= 65536), "The port is wrong type or value range"
        assert isinstance(attempts, int) and (0 <= attempts), "The attempts parameter is not the same value"
        # Assembling the port and the ip to the address tuple
        address = (ip, port)
        # Calling the connect of the socket as many times as specified
        while not self.connected:
            try:
                # Delaying the try possibly
                time.sleep(delay)
                # Attempting to build the connection
                self.sock.connect(address)
                # Updating the connected status to True
                self.connected = True
            except Exception as exception:
                # Closing the socket and creating a new one, which is gonna be used in the next try
                self.sock.close()
                self.sock = socket.socket(self.family, self.type)
                self.connected = False
                # Decrementing the counter for the attempts
                attempts -= 1

        # In case the loop exits without the connection being established
        if self.attempts == 0:
            raise ConnectionRefusedError("The socket could not connect to {}".format(address))

    def receive_until_character(self, character, limit, timeout=None, include=False):
        """
        This method receives data from the wrapped socket until the special 'character' has been received. The limit
        specifies after how many bytes without the termination character a Error should be raised. The timeout
        is the amount of seconds every individual byte is allowed to take to receive before raising an error. The
        include flag tells whether the termination character should be included in the returned data.
        Args:
            character: can either be an integer in the range between 0 and 255, that is being converted into a
                character or can be a bytes object/ bytes string of the length 1. After receiving this byte the data
                up to that point is returned.
            limit: The integer amount of bytes, that can be received without terminating, without raising an error.
            timeout: The float amount of seconds each individual byte is allowed to take to receive before a
                Timeout is raised.
            include: The boolean flag of whether to include the termination character in the return or not

        Returns:
        The data bytes, that were received up to the point, when the termination character was received
        """
        # Checking for the data type fo
        is_bytes = isinstance(character, bytes)
        is_int = isinstance(character, int)
        assert (is_bytes and len(character) == 1) or (is_int and 0 <= character <= 255)
        # In case the input is an integer converting it into a bytes object
        if is_int:
            character = int.to_bytes(character, "1", "big")

        counter = 0
        # Calling the receive length function with one byte at a time until the character in question appears
        data = b""
        while True:
            # Checking if the limit of bytes has been reched
            if counter > limit:
                raise OverflowError("The limit of bytes to receive until character has been reached")
            current = self.receive_length(1, timeout)
            if current == character:
                if include is True:
                    data += character
                # After the character has been found and eventually was added to the data, breaking the infinite loop
                break
            else:
                # In case the character is not there adding the byte to the counter and incrementing the counter
                data += current
                counter += 1
        return data

    def receive_line(self, limit, timeout=None):
        """
        This method simply calls the method for receiving until a character with the newline character to receive one
        line of data
        Args:
            limit:
            timeout:

        Returns:

        """
        return self.receive_until_character(b"\n", limit, timeout=timeout)

    def receive_length(self, length, timeout=None):
        """
        This method receives a certain amount of bytes from the socket object, that is being wrapped. It is also
        possible to specify the amount of time the method is supposed to wait for the next character to be received
        before issuing a timeout.
        Raises:
            EOFError: In case the data stream terminated before the specified amount of bytes was received
            ConnectionError: In case the socket object in question is not connected yet.
            TimeoutError: In case it took to long to receive the next byte
        Args:
            length: The integer amount of bytes to be received from the socket
            timeout: The float amount of time, that is tolerated for a byte to be received

        Returns:
        The bytes string of the data with the specified length, received from the socket
        """
        # First checking whether or not there actually is a callable socket within the 'connection' attribute, by
        # checking the 'connected' flag. In case there is not, will raise an exception
        if not self.connected:
            raise ConnectionError("There is no open connection to receive from yet!")

        start_time = time.time()
        data = b''
        while len(data) < length:
            # receiving more data, while being careful not accidentally receiving too much
            more = self.sock.recv(length - len(data))

            # In case there can be no more data received, but the amount of data already received does not match the
            # amount of data that was specified for the method, raising End of file error
            if not more:
                raise EOFError("Only received ({}/{}) bytes".format(len(data), length))

            # Checking for overall timeout
            time_delta = time.time() - start_time
            if (timeout is not None) and time_delta >= timeout:
                raise TimeoutError("{} Bytes could not be received in {} seconds".format(length, timeout))

            # Adding the newly received data to the stream of already received data
            data += more
        return data

    def sendall(self, data):
        """
        Simply wraps the 'sendall' method of the actual socket object.
        Raises:
            ConnectionError: In case the socket is not connected yet.
        Args:
            data: The data to be sent over the socket, best case would be bytes already, does not have to be though

        Returns:
        void
        """
        # Checking if the socket is already connected
        if not self.connected:
            raise ConnectionError("There is no open connection to send to yet!")
        # Actually calling the method of the socket
        if isinstance(data, bytes):
            self.sock.sendall(data)
        elif isinstance(data, str):
            self.sock.sendall(data.encode())
        else:
            raise TypeError("The data to send via socket has to be either string or bytes")

    def release_socket(self):
        """
        This method releases the socket from the wrapper, by setting the internal property to the socket to None and
        returning the wrapper
        Returns:
        The socket, that was used by the wrapper
        """
        # Removing the pointer to the socket from the object property and returning the socket
        sock = self.sock
        self.sock = None
        return sock

    def appoint_family(self):
        """
        This method simply sets the family attribute of the object to the same value as the family property of the
        socket, that is being wrapped
        Returns:
        void
        """
        self.family = self.sock.family

    def appoint_type(self):
        """
        this method simply sets the type property of the object to the same value as the type property of the
        socket, that is being wrapped.
        Returns:
        void
        """
        self.type = self.sock.type


class Connection:
    """
    ABSTRACT BASE CLASS

    GENERAL:
    One problem one might encounter with networking code is that while sockets are the most basic construct to be used
    and therefore also to be preferred as the basic building block of network code such as the form transmission
    protocol, the sockets might also not always works with other frameworks or even the platform the code is running on.
    A good example would be using Python with kivy on android, sockets themselves behave very problematic and as a
    developer your best choice is to use the twisted framework for network com. And if one wishes to use the protocol
    framework even then, all of the classes would have to be rewritten, but if a abstract encapsulation of the network
    such as the Connection objects would be used as the basic building block for the networking, the twisted
    functionality could simply be implemented and hidden behind a new type of Connection instance and the whole
    frameworks would still work.

    This abstract implementation also allows the protocol framework to be used in other fields as well, for example a
    Connection object could be build as a shared state between two Threads, or a Pipe between two processes. Even
    a really slow running communication based on emails could be capsuled to be managed by the protocol framework.

    The Connection object is build as something like a bidirectional socket, that implements behaviour for sending
    string data as well as receiving string and bytes data.
    """
    def __init__(self):
        pass

    def sendall_string(self, string):
        """
        A Connection object obviously has to implement the functionality of sending a string over the connection
        Args:
            string: The string to be sent to the the other side of the connection

        Returns:
        void
        """
        raise NotImplementedError()

    def sendall_bytes(self, bytes_string):
        """
        A Connection object also has to be able to send raw bytes data over the connection
        Args:
            bytes_string: The bytes string object to be sent

        Returns:
        void
        """
        raise NotImplementedError()

    def receive_length_string(self, length, timeout):
        """
        A Connection object has to be able to receive only a certain length of string from the communication
        Args:
            length: The amount of characters or the int length of the string supposed to be receuved from the
            connection.
            timeout: The float amount of time the reception of the string is allowed to take until a Timeout Error
                is being raised

        Returns:
        The received string
        """
        raise NotImplementedError()

    def receive_length_bytes(self, length, timeout):
        """
        A Connection object has to be able to receive bytes data of a certain (character-) length correctly
        Args:
            length: The amount of characters or the int length of the string supposed to be receuved from the
            connection.
            timeout: The float amount of time the reception of the string is allowed to take until a Timeout Error
                is being raised

        Returns:
        The received bytes string object
        """
        raise NotImplementedError()

    def wait_length_string(self, length):
        """
        The wait method is equal to the equally named receive method except for the fact, that it does not implement a
        timeout on purpose for situations where one wants to infinitely wait to receive from a connection.
        Args:
            length: The amount of characters or the int length of the string supposed to be receuved from the
            connection.

        Returns:
        The received string
        """
        raise NotImplementedError()

    def wait_length_bytes(self, length):
        """
        This method will be used to wait an indefinte amount of time for the reception of a byte string from the
        connection
        Args:
            length: The amount of characters or the int length of the string supposed to be receuved from the
            connection.

        Returns:
        the received byte string
        """
        raise NotImplementedError()

    def receive_line(self, timeout):
        """
        A Connection object has to be able to receive a line from the stream
        Args:
            timeout: The float amount of time the reception of the string is allowed to take until a Timeout Error
                is being raised
        Returns:
        A string up until a new_line character has been received from the connection
        """
        raise NotImplementedError()

    def receive_string_until_character(self, character, timeout):
        """
        A Connection object has to be able to receive a string until a special break character has been received
        Args:
            character: The string character with the length one, which is supposed to be received
            timeout: The float amount of time the reception of the string is allowed to take until a Timeout Error
                is being raised
        Raises:
            TimeoutError: In case the process of receiving exceeds the amount of time specified
        Returns:
        A string up until a special line character has been received
        """
        raise NotImplementedError()

    def receive_bytes_until_byte(self, byte, timeout):
        """
        This method will be used to receive a byte string until a special break character (also byte string) occurred
        in the stream
        Args:
            byte: The byte string character after which to return the received sub byte string
            timeout: The float amount of time the reception of the string is allowed to take until a Timeout Error
                is being raised

        Returns:
        The received byte string
        """
        raise NotImplementedError()

    def wait_string_until_character(self, character):
        """
        The wait method is equal to the equally named receive method except for the fact, that it does not implement a
        timeout on purpose for situations where one wants to infinitely wait to receive from a connection.
        Args:
            character: The character after which to return the substring up to that point

        Returns:
        The string received
        """
        raise NotImplementedError()

    def wait_bytes_until_byte(self, byte):
        """
        This method will be used to wait an indefinite amount of time until a special break byte string will be read
        from the stream and then return the byte string received up until then.
        Args:
            byte: The byte string object of length one after which the received is to be returned

        Returns:
        The received bytes string
        """
        raise NotImplementedError()

    @staticmethod
    def _check_timeout(timeout):
        """
        This is a utility method, that checks if a passed value for a timeout is actually a int or a float
        Raises:
            TypeError: If the specified timeout value is not a proper value of float or int type
        Args:
            timeout: The timeout value to check

        Returns:
        void
        """
        if not (isinstance(timeout, int) or isinstance(timeout, float)):
            raise TypeError("The timeout has to be a int value")

    @staticmethod
    def _check_character(character):
        """
        This is a utility method, that checks if a passed value for a character param is actually a string and also if
        that string actually has the length one
        Raises:
            TypeError: In case the passed value is not even a string
            ValueError: In case the passed string is not of the length one
        Args:
            character: The value to check

        Returns:
        void
        """
        if not isinstance(character, str):
            raise TypeError("The character has to be a string")
        if not len(character) == 1:
            raise ValueError("The character string has to be length one")

    @staticmethod
    def _check_byte(byte):
        """
        This is a utility function for checking if a passed byte parameter value actually is of the bytes type and has
        the required length one.
        Args:
            byte: The value to check

        Returns:
        void
        """
        if not isinstance(byte, bytes):
            raise TypeError("The byte param has to be a bytes string object")
        if not len(byte) == 1:
            raise ValueError("the byte param object has to be a byte string of the length one")

    @staticmethod
    def _check_length(length):
        """
        This is a utility function for checking if a passed value for the length of a string is actually a int value
        and if that value is positive.
        Args:
            length: The value in question

        Returns:
        void
        """
        if not isinstance(length, int):
            raise TypeError("The length parameter has to be int")
        if not length > 0:
            raise ValueError("The length has to be a positive value")


class SocketConnection(Connection):
    """
    This is a subclass of the Connection object and therefore a direct implementation of its abstract methods. This
    class uses the network communication via socket objects to ensure the receive/send functionlity guaranteed for
    a Connection object.
    """
    def __init__(self, sock):
        Connection.__init__(self)
        self.sock = sock

    def sendall_bytes(self, bytes_string):
        """
        This method is used to send a bytes string over the connection
        Args:
            bytes_string: The bytes string to send

        Returns:
        void
        """
        self.sock.sendall(bytes_string)

    def sendall_string(self, string):
        """
        This method is used to send a string over the connection
        Args:
            string: The string to be sent

        Returns:
        void
        """
        self.sendall_bytes(string.encode())

    def receive_line(self, timeout):
        """
        This method will receive one line from the connection, which means, the string until a new line character
        occurred.
        Args:
            timeout: The max amount of time for the reception

        Returns:
        The received string
        """
        return self.receive_string_until_character("\n", timeout)

    def receive_length_string(self, length, timeout):
        """
        This method will receive a specified length of string
        Args:
            length: The int length of the string to receive
            timeout: The max amount of time for the reception

        Returns:
        The received string
        """
        byte_string = self.receive_length_bytes(length, timeout)
        return byte_string.decode()

    def receive_length_bytes(self, length, timeout):
        """
        This method will receive a specified length of byte string
        Args:
            length: The length of the byte string to receive
            timeout: The max amount of time for the reception

        Returns:
        The received byte string
        """
        self._check_timeout(timeout)
        self._check_length(length)
        # Setting up the list wich will contain the data already received
        data = b''
        # Setting up the time for the timeout detection
        start_time = time.time()
        while len(data) < length:
            received = self.sock.recv(length - len(data))

            # Checking if there is nothing to receive anymore, before the specified amount was reached
            if not received:
                raise EOFError("Only received ({}|{}) bytes from the socket".format(len(bytes), bytes))

            # Checking for overall timeout
            time_delta = time.time() - start_time
            if time_delta > timeout:
                raise TimeoutError("{} Bytes could not be received in {} seconds".format(length, timeout))

            data += received

        return data

    def wait_length_string(self, length):
        """
        This method will wait an indefinite amount of time to receive a string of the specified length
        Args:
            length: The int length of the string to receive

        Returns:
        The received string
        """
        bytes_string = self.wait_length_bytes(length)
        return bytes_string.decode()

    def wait_length_bytes(self, length):
        """
        This method will wait an indefinite amount of time to receive a bytes string of the specified length
        Args:
            length: The length of the byte string to receive

        Returns:
        The received byte string
        """
        self._check_length(length)
        # Setting up the list which will contain the data already received
        data = b''
        while len(data) < length:
            received = self.sock.recv(length - len(data))

            # Checking if there is nothing to receive anymore, before the specified amount was reached
            if not received:
                raise EOFError("Only received ({}|{}) bytes from the socket".format(len(bytes), bytes))

            data += received

        return data

    def receive_string_until_character(self, character, timeout):
        """
        This function will receive from the socket until the specified break character has been read in the stream.
        After that the substring, that has been received up until that point will be returned
        Args:
            character: the string break character
            timeout: The max amount of time for the reception

        Returns:
        The received string
        """
        self._check_character(character)
        byte_character = character.encode()
        bytes_string = self.receive_bytes_until_byte(byte_character, timeout)
        return bytes_string.decode()

    def receive_bytes_until_byte(self, byte, timeout):
        """
        This function will receive the bytes string and return the sub string until a special break byte character
        has occurred in the stream
        Args:
            byte: The byte string character after which to return the sub string before
            timeout: The max time for the reception

        Returns:
        The received bytes string
        """
        # Raising error in case wrong values have been passed as parameters
        self._check_byte(byte)
        self._check_timeout(timeout)
        # Setting up for the timeout watch
        start_time = time.time()
        # The list of byte string data, which is later going to contain the string to return
        data = []
        # The temporary string received
        received = b''
        while byte != received:
            received = self.sock.recv(1)

            # Checking if there is nothing to receive anymore, before the specified amount was reached
            if not received:
                raise EOFError("Only received ({}|{}) bytes from the socket".format(len(bytes), bytes))

            # Checking for overall timeout
            time_delta = time.time() - start_time
            if time_delta > timeout:
                raise TimeoutError("Bytes could not be received in {} seconds".format(timeout))

            data.append(received)
        # Removing the break character from the data list
        data.pop(-1)
        # Returning the assembled bytes string
        return b''.join(data)

    def wait_string_until_character(self, character):
        """
        This method will wait an indefinite amount of time until the break character has been received and then
        return the sub strung received up to that point
        Args:
            character: The string character to act as breaking point in the reception

        Returns:
        The received string
        """
        self._check_character(character)
        byte_character = character.encode()
        bytes_string = self.wait_bytes_until_byte(byte_character)
        return bytes_string.decode()

    def wait_bytes_until_byte(self, byte):
        """
        This method will wait an indefinite amount of time until the break byte character has been received and then
        return the sub string received up to that point.
        Args:
            byte: The byte string character

        Returns:
        The received byte string
        """
        # Raising error in case wrong values have been passed as parameters
        self._check_byte(byte)
        # The list of byte string data, which is later going to contain the string to return
        data = []
        # The temporary string received
        received = b''
        while byte != received:
            received = self.sock.recv(1)

            # Checking if there is nothing to receive anymore, before the specified amount was reached
            if not received:
                raise EOFError("Only received ({}|{}) bytes from the socket".format(len(bytes), bytes))

            data.append(received)
        # Removing the break character from the data list
        data.pop(-1)
        # Returning the assembled bytes string
        return b''.join(data)

# THE FORM TRANSMISSION PROTOCOL


class AppendixEncoder:
    """
    INTERFACE
    This is a base class acting as an interface for the different appendix encoder variations.
    The appendix encoder classes are supposed to be static classes implementing the two methods 'encode' and 'decode'
    with which the appendix of a form object can be encoded into a bytestring format, which can be transported over
    a network socket and then be decoded by a form object on the receiving end.

    Notes:
    The different encoder classes are supposed to provide more variance to what kind of objects can be transmitted as
    the appendix of the 'Form' class. Because these encoder classes are mainly used by the Form object to encode and
    decode the appendix objects, theses processes have to be designed for exactly that purpose.
    """
    def __init__(self):
        pass

    @staticmethod
    def encode(obj):
        """
        The encode method is supposed to take any object, that is valid for the specific implementation of the encoding
        and return the byte string representation.
        Args:
            obj: Any type of object, that can be encoded by the chosen method

        Returns:
        a string representation of that object
        """
        raise NotImplementedError("This method has to be overwritten")

    @staticmethod
    def decode(byte_string):
        """
        The decode method is supposed to take a string object and turn it back into the object, that was originally
        encoded using the same method
        Args:
            byte_string: The byte string, which is the encoded format of the received object

        Returns:
        Any kind of object, that was subject to the encoding process
        """
        raise NotImplementedError("This method has to be overwritten!")

    @staticmethod
    def is_serializable(obj):
        """
        This method is supposed to return a boolean value, that indicates whether the passed object can be serialized
        by the method of the specific encoder, which sub classes this base class of appendix encoding.
        Args:
            obj: The object to attempt

        Returns:
        The boolean value if the value can be serialized
        """
        raise NotImplementedError("This method has to be overwritten!")


class JsonAppendixEncoder(AppendixEncoder):

    @staticmethod
    def encode(obj):
        """
        This method will use the json dumps functionality to turn the iterable object given into a json string and
        then return the bytes representation of that string.
        Args:
            obj: Any kind of object, that is naturally json serializable, which is most of the python native iterables

        Returns:
        The byte string representation of the object
        """
        json_string = json.dumps(obj)
        byte_string = json_string.encode()
        return byte_string

    @staticmethod
    def decode(byte_string):
        """
        Thus method will use the json loads functionality to turn the byte string object given back into a string using
        the regular utf 8 decoding and then attempting to json load the original object from that string.
        Notes:
            In case the byte string obe
        Args:
            byte_string: The bytes object, that was originally a object encoded with json

        Returns:
        The object, stored as the byte string
        """
        # Turning the bytes back into the json string first
        json_string = byte_string.decode()
        # Adding the special case for an empty string
        if len(json_string.strip()) == 0:
            return []
        # Loading the json object from the string & returning
        obj = json.loads(json_string)
        return obj

    @staticmethod
    def is_serializable(obj):
        """
        Returns whether the passed object can be json serialized or not
        Args:
            obj: The object in question

        Returns:
        the boolean value
        """
        try:
            JsonAppendixEncoder.encode(obj)
            return True
        except:
            return False


class PickleAppendixEncoder(AppendixEncoder):
    """
    This class provides the static methods to encode a appendix object using the pickle mechanism, which enables the
    use of more complex and custom objects.
    """
    @staticmethod
    def encode(obj):
        """
        This method uses the python native pickle dumps functionality to directly turn the given object into a byte
        string
        Args:
            obj: The object to convert

        Returns:
        The pickled byte string
        """
        byte_string = pickle.dumps(obj)
        return byte_string

    @staticmethod
    def decode(byte_string):
        """
        This method calls the pickle loads on the given byte string to load the encoded object
        Args:
            byte_string: The byte string representation of the encoded object

        Returns:
        The original object
        """
        obj = pickle.loads(byte_string)
        return obj

    @staticmethod
    def is_serializable(obj):
        """
        This method returns whether or not the object passed can be serialized by pickle
        Args:
            obj: The object in question

        Returns:
        boolean value
        """
        try:
            PickleAppendixEncoder.encode(obj)
            return True
        except:
            return False


class Form:
    """
    GENERAL
    A form represents a special kind of data type, which imposes some restrictions as to what kind of data can be
    represented, but works directly with network protocols and can be transmitted more easily. A Form consists of the
    3 parts:
    - TITLE: The title is a single line string, that specifies the rough function of the form
    - BODY: The Body can be any kind of string block. It should be organized in new lines, as that is how it is being
      transmitted later on
    - APPENDIX: The appendix is supposed to represent the part of a message, which cannot be easily turned into a
      string, organized by newlines. This can be almost any data structure with the only limitation of being able to
      be turned into a json.
    The form is sort aof a base structure for communication, as the three parts of data can be used and assigned
    meaning by special protocols later on. The form objects just provide the blank skeleton of a message

    CONSTRUCTION
    A form object has to be passed the three arguments: title, body and appendix.
    The title has to be a single line string (which means, there cannot be a newline character in there). The body can
    either be a string all together or a list of items (which one has to be able to convert to strings) which are then
    internally being turned into the expected string structure.
    The appendix is special, if it is a string it is being interpreted as already being a json string and it is
    attempted to load the data, any other data type will be attempted to be converted into a json string!

    Attributes:
        title: The string title of the Form
        body: The string block, organized by new line characters
        appendix_json: The Json string of the data to be represented by the appendix
        appendix: The actual data object, described by the json string
    """
    def __init__(self, title, body, appendix, appendix_encoder=JsonAppendixEncoder):
        self.title = title
        self.body = body
        self.appendix = appendix
        self.appendix_encoded = None
        self.appendix_encoder = appendix_encoder

        # Checking if the title is a string without a new line, as needed
        self.check_title()
        # Assuring, that the body is one single string, as it has to be
        self.evaluate_body()
        # Json the appendix in case it is raw data, attempting to load in case it is a string
        self.evaluate_appendix()

    def evaluate_body(self):
        """
        The body parameter can either be a string or a list of items (which have to be able to be turned into strings),
        but the objects needs the body property to be a string. Thus this method checks for the requirements of type
        etc. to match and turns the list into a string with newline seperation of the characters.
        Raises:
            TypeError: In case the body attribute is neither string nor list
            ValueError: In case the items of the list cannot be turned into a string
        Returns:
        None
        """
        # Checking the body attribute for the requirements
        self.check_body()
        if isinstance(self.body, list):
            # Since the body attribute has been checked, it is safe to assume every item can be converted into string
            body_string_map = map(str, self.body)
            body_string_list = list(body_string_map)
            # Producing a string, that separates the strings in this list by a newline character
            body_string = '\n'.join(body_string_list)
            # Setting the body to be the assembled
            self.body = body_string

    def evaluate_appendix(self):
        """
        The appendix can be anything, with the limitation, that it can be turned into a json string. In case that is
        possible this method will do that and assign the string to the appendix attribute.
        Raises:
            ValueError: In case the object cannot be turned into a json
        Returns:
        void
        """
        # In case the appendix is a string it is being interpreted as already in json format and thus trying to unjson
        if isinstance(self.appendix, bytes):
            try:
                # Attempting to use the encoder to encoder to decode the bytes string
                self.appendix_encoded = self.appendix
                appendix_decoded = self.appendix_encoder.decode(self.appendix_encoded)
                self.appendix = appendix_decoded
            except ValueError as value_error:
                raise value_error
            except TypeError as type_error:
                raise type_error
        # All other data types are interpreted as raw data and are being jsoned
        else:
            try:
                self.appendix_encoded = self.appendix_encoder.encode(self.appendix)
            except ValueError as e:
                raise e

    @property
    def empty(self):
        """
        This property tells whether the form is empty, meaning both the appendix and the body being a empty string
        Returns:
        the boolean value of whether or not the body and the appendix are empty
        """
        return len(self.body) == 0 and len(self.appendix) == 0

    @property
    def valid(self):
        """
        This property tells whether or not the form qualifies as being valid. A form is invalid if either the title is
        a empty string or only whitespaces or the body and the appendix being completely empty (here a single whitespace
        would be valid)
        Returns:
        The boolean value of whether or not the form is valid
        """
        # stripped refers to as being stripped of all its whitespaces
        stripped_title = self.title.replace(" ", "")
        if len(stripped_title) == 0:
            return False
        elif self.empty:
            return False
        else:
            return True

    def check_attributes(self):
        """
        This function checks the attributes for correct data types.
        The body attribute has to be either one big string or a list of objects, that can be turned into strings. The
        title has to be a string without a newline character.
        Raises:
            TypeError
            ValueError
        Returns:
        void
        """
        # Checking the body and the title to be the correct data type
        self.check_body()
        self.check_title()

    def check_title(self):
        """
        This method will simply check the title attribute of the object for the correct type, which is supposed to be
        a string.
        Raises:
            TypeError: In case the title attribute is not a string
        Returns:
        void
        """
        if not isinstance(self.title, str):
            raise TypeError("The title has to be a string object")
        # Checking if the given string is one lined string
        else:
            if "\n" in self.title:
                raise ValueError("The title string has to be single line!")

    def check_body(self):
        """
        This method will simply check the attribute of the objects body property.
        The body can be one of the following data types:
        - A string
        - A list with strings or objects, that can be converted to strings
        Raises:
            TypeError: In case the objects in the list cannot be turned into strings, or are neither string nor list
        Returns:
        void
        """
        # The body being a string would be the most common case
        if not isinstance(self.body, str):
            if isinstance(self.body, list):
                # In case one item cannot be turned into a string, will be deleted
                for item in self.body:
                    try:
                        str(item)
                    except ValueError:
                        raise TypeError("The list for the body must only contain items, that can be strings")
            else:
                raise ValueError("The body attribute must either be a string or a list os strings")

    def __eq__(self, other):
        """
        The magic method for comparing two form objects. Two form objects are equal if the title, the body and the
        appendix are equal
        Args:
            other: The other Form object to test

        Returns:
        boolean value of whether or not they are equal
        """
        if isinstance(other, Form):
            same_title = other.title == self.title
            same_body = other.body == self.body
            same_appendix = other.appendix == self.appendix
            if same_title and same_body and same_appendix:
                return True
        return False


class FormTransmitterThread(threading.Thread):
    """
    GENERAL
    This is a Thread. The Thread is supposed to be passed a socket, which has an already open connection to a Thread
    on the other side, which receives the Form data as a counterpart to this one. This Thread is used to transmit a
    Form object. The title of the form is being sent first and after that the individual lines of the forms string
    body are being transmitted before the separation (a special string, that can also be specified) is being sent with
    the length of the string of the forms appendix.
    In between each sending the receiving end is supposed to be sending an ACK message. In case the ACK is not sent in
    the specified amount of time for the timeout the communication is stopped.

    SEPARATION COLLISIONS:
    The separation string is supposed to be a definite sign, that the body of the form is now finished and that the
    appendix starts now. In case the separation string is already the front part of a line in the body of the form
    that would lead to an error. Through the 'adjust' parameter it can be set, that the body is being searched for
    ocurrances of the separation string and then adjusted, so that they would not be recognised, by adding a whitespace
    at the front of the line. In case the adjust is False, the body will be searched for the separation string and
    an exception risen in case one was found
    """
    def __init__(self, connection, form, separation, timeout=10, adjust=True):
        threading.Thread.__init__(self)
        # The form object to be transmitted over the socket connection
        self.form = form
        self.check_form()
        # The socket and the wrapped socket
        self.connection = connection
        # A string to be separating the body from the appendix
        self.separation = separation
        self.check_separation()

        if adjust:
            self.adjust_body_string()
        else:
            self.check_body_string()

        # The timeout of receiving the ack after a sending
        self.timeout = timeout
        # The state variables of the Thread and the transmission
        self.running = False
        self.finished = False

    def run(self):
        self.running = True
        self.send_title()
        self.wait_ack()
        self.send_body()
        self.wait_ack()
        self.send_appendix()
        self.wait_ack()

        # Updating the state variables
        self.running = False
        self.finished = True

    def send_body(self):
        """
        This method simply pushes the complete body string into the socket connection
        Returns:
        void
        """
        # Sending the individual lines of the body of the form over the socket
        body_string_lines = self.form.body.split("\n")
        for line in body_string_lines:
            self.connection.sendall_string(line+"\n")
            self.wait_ack()
        # Sending the separation at last
        separator = self.assemble_separator()
        self.connection.sendall_string(separator+"\n")

    def send_title(self):
        title = self.form.title + "\n"
        self.connection.sendall_string(title)

    def send_appendix(self):
        """
        This method will send the appendix in form of the json string
        Returns:
        void
        """
        appendix_encoded = self.form.appendix_encoded
        self.connection.sendall_bytes(appendix_encoded)

    def wait_ack(self):
        """
        This method will wait and receive an ACK.
        Raises:
            TimeoutError: If the specified timeout error is exceeded while waiting for the ACK
        Returns:
        void
        """
        response = self.connection.receive_length_bytes(3)
        if not response == b'ack':
            raise ValueError("Incorrect ACK sent")

    def check_form(self):
        """
        This method checks the form attribute of the object. The form attribute has to be a Form object (whose class
        can be found in the very same module), additionally the Form object has to be valid, which is the case if it
        has a none empty body and appendix and a title none empty and not only whitespaces.
        Raises:
            TypeError: In case the form attribute is not a Form object
            ValueError: In case the Form object is not 'valid'
        Returns:
        void
        """
        if isinstance(self.form, Form):
            # In case it actually is a form, the form also has to be valid
            if not self.form.valid:
                raise ValueError("The passed Form object has to be valid")
        else:
            raise TypeError("The form attribute has to be a Form object")

    def check_separation(self):
        """
        Checks the separation attribute. The separation attribute has to be a string, which is None empty and a single
        line.
        Raises:
            TypeError: In case the separation attribute is not a string
            ValueError: In case the string is empty or the string has more than one line
        Returns:
        void
        """
        if isinstance(self.separation, str):
            # Checking for the possibility of a multi line separation string
            if "\n" in self.separation:
                raise ValueError("The separation has to be a one line string")
            # Checking for the possibility of a empty separation string
            stripped_separation = self.separation.replace(" ", "")
            if len(stripped_separation) == 0:
                raise ValueError("The separation has to be a None empty string")
        else:
            raise TypeError("The separation has to be a string")

    def check_body_string(self):
        """
        Checking the body string for a occurance of the separation string and raising an error in case the is a
        collision of the separation string in the body of the form
        Returns:
        void
        """
        form_body_string = self.form.body
        form_body_lines = form_body_string.split("\n")
        for i in range(len(form_body_lines)):
            if form_body_lines[i][:len(self.separation)] == self.separation:
                raise ValueError("There is a collision of the separation string in the form body")

    def assemble_separator(self):
        """
        This method will assemble the string to send as separation from the
        Returns:
        The string consisting of the separation string and the length of the appendix
        """
        appendix = self.form.appendix_encoded
        appendix_length = len(appendix)
        return ''.join([self.separation, str(appendix_length)])

    def adjust_body_string(self):
        """
        This method adjusts the body string of the form to transmit by appending a whitespace character to the front
        of all the lines, that match the separation string. If lines from the form body, this would cause an error
        in the loading of the appendix.
        Notes:
            This method assumes, that the separation and the form attribute of the object is correctly set, so this
            method is not to be called in before initializing those parameters
        Returns:
        void
        """
        form_body_string = self.form.body
        form_body_lines = form_body_string.split("\n")
        for i in range(len(form_body_lines)):
            if form_body_lines[i][:len(self.separation)] == self.separation:
                form_body_lines[i] = " " + form_body_lines[i]
        form_body_string = "\n".join(form_body_lines)
        self.form.body = form_body_string


class FormReceiverThread(threading.Thread):

    def __init__(self, connection, separation, timeout=10):
        threading.Thread.__init__(self)
        # The socket and the wrapped socket
        self.connection = connection
        # A string to be separating the body from the appendix
        self.separation = separation

        # The timeout of receiving the ack after a sending
        self.timeout = timeout
        # The state variables of the Thread and the transmission
        self.running = False
        self.finished = False
        # The variable for the length of the appendix to receive
        self.appendix_length = None
        # All the variables holding the relevant values for the form object
        self.title = None
        self.body = None
        self.appendix = None
        self.form = None

    def run(self):
        self.running = True
        self.receive_title()
        self.send_ack()
        self.receive_body()
        self.send_ack()
        self.receive_appendix()
        self.send_ack()
        self.assemble_form()
        self.running = False
        self.finished = True

    def receive_form(self):
        """
        This method will be blocking until the finished flag of the object was set to True and then return the
        received form object
        Returns:
        The Form object received through the socket
        """
        while not self.finished:
            time.sleep(0.001)
        return self.form

    def receive_title(self):
        """
        This method receives a single line and assigns that line as the title of the form. Because it does so, this
        method has to be called as the first method when beginning a form transmission.
        Returns:
        void
        """
        line = self.receive_line()
        self.title = line

    def receive_body(self):
        """
        This method will receive the body of the form, by receiving line for line until the separation line has been
        received. The separation line will then be processed into the length of the appendix and the received lines
        will be processed into the body string
        Returns:
        void
        """
        is_separation = False
        line_list = []
        line = None
        # Receiving new lines from the socket, until the separation line has been received
        while not is_separation:
            line = self.receive_line()
            is_separation = self.checkup_separation(line)
            if not is_separation:
                line_list.append(line)
                # Sending the ack
                self.send_ack()
        # If the while loop exits, that means the separation has been sent and is now the last line that was received
        # which means the string is still inside the line variable
        self.process_separation(line)

        # Assembling the line list into the body string and assigning it to the body
        body_string = '\n'.join(line_list)
        self.body = body_string

    def receive_appendix(self):
        """
        This method will receive the appendix data from the socket, by receiving exactly as many bytes as the length
        extracted from the separation string
        Returns:
        void
        """
        # Receiving as many bytes as the length was dictated by the separation string
        appendix_bytes = self.connection.receive_length_bytes(self.appendix_length, timeout=self.timeout)
        appendix_string = appendix_bytes
        self.appendix = appendix_string

    def receive_line(self):
        """
        This method will receive a line from the socket as a bytes string object and then turn the byte string back
        into a regular string, assuming the standard encoding
        Returns:
        The string line, received from the socket
        """
        return self.connection.receive_line(self.timeout)

    def process_separation(self, line):
        """
        This method will take the separation line, check it for its validity and in case it is correct extract the
        appendix length from the string and then assign this length to the length attribute of this object
        Args:
            line: the string line to be processed for the length of the appendix

        Returns:
        void
        """
        # Checking if this actaully is the separation string line
        self.check_separation(line)
        # Removing the actual separation string from the line
        length_string = line.replace(self.separation, "")
        length_string.strip()
        # Turning the string into a number
        length = int(length_string)
        # Assigning that length value to the designated attribute of this object
        self.appendix_length = length

    def assemble_form(self):
        """
        This method will use all the data received through the socket and saved in the objects attributes to build a
        new form object.
        Raises:
            ValueError: In case the form has not been completely received yet
        Returns:
        void
        """
        # Checking if all the data has been received and if it is save to assemble a Form object from that data
        self.check_form()
        # Building the Form object from the received data
        form = Form(self.title, self.body, self.appendix)
        self.form = form

    def check_separation(self, line):
        """
        This method checks, whether the passed object is a string and then also checks if that string is actually the
        separation string by calling the checkup method for the separation string. An exception will be risen in case
        either one of the conditions is not met.
        This method is used to assure, that the correct object is being used for further processing
        Raises:
            ValueError
            TypeError
        Args:
            line: The string line, which is supposed to be the separation string

        Returns:
        void
        """
        # Raising an error, in case the passed object is not a string or not the separation string
        if not isinstance(line, str):
            raise TypeError("The passed line is not even a string")
        if not self.checkup_separation(line):
            raise ValueError("The passed line is not the separation string")

    def check_form(self):
        """
        This method checks if all the attribute of this object, that were supposed to contain the form data actually
        contain data other than None and thus checking if it is save to assemble a form object.
        Raises:
            ValueError
        Returns:
        void
        """
        if self.title is None or self.body is None or self.appendix is None:
            raise ValueError("The form data has not been completely received")

    def checkup_separation(self, line):
        """
        This method checks whether the the passed line string is the separation line, that is meant to separate the
        body from the appendix and returns the boolean value of that being the case ot not
        Args:
            line: The string of the receuved line to check

        Returns:
        The boolean value of the line being the separation line or not
        """
        # The first condition of the line being the separation is it being longer than the sep string alone
        if len(line) > len(self.separation):
            separation_length = len(self.separation)
            if line[:separation_length] == self.separation:
                return True
        # In case one of the conditions was not given, False is returned
        return False

    def send_ack(self):
        """
        This method simply sends a string with the ack to the transmitting end, wo signal, that the connection is still
        active
        Returns:
        void
        """
        self.connection.sendall_bytes(b"ack")


# THE COMMANDING PROTOCOL


class CommandContext:
    """
    BASE CLASS
    This is the base class for all specific CommandContext objects. The command context objects are supposed to be
    providing the necessary implementations for the commands used by the CommandingProtocol.

    CREATING COMMAND CONTEXTS
    Commands can be added to the functionality of a specific command set implementation by having a new specialized
    subclass inherit from this CommandContext class and adding new methods, whose names start with 'command' and an
    underscore, followed by the (exact!) name of the command whose functionality is to be implemented:
    Example: def command_print(self, pos_args, kw_args): ...

    EXECUTING COMMANDS:
    The commandContext objects ca be used to directly execute commands, described by a CommandingForm sub class, by
    being passed to the execute method.
    """
    def __init__(self):
        pass

    def execute_form(self, form):
        """
        A CommandingForm subclass can be passed to this method and the action corresponding to the type of form will be
        executed: In case it is a CommandForm, the command will be executed and the return Value will be returned, in
        case it is a ReturnForm the stored return value will be returned
        Args:
            form: The CommandingForm subclass to be executed

        Returns:
        Either the return of the executed command or the return value of a remote executed function
        """
        if isinstance(form, CommandingForm):
            if isinstance(form, CommandForm):
                # Getting the method, that actually executes the behaviour for that command
                command = self.lookup_command(form.command_name)
                # Executing the command with the pos and kw args
                return command(*form.pos_args, **form.key_args)
            elif isinstance(form, ReturnForm):
                # Simply returning the value stored in the form
                return form.return_value
        else:
            raise TypeError("The form to execute is supposed to be a CommandingForm subclass")

    def lookup_command(self, command_name):
        """
        This method will use the command name given and first assemble the corresponding method name for that command
        name and then it will attempt to get the attribute of this very command context object. If a method exists,
        that implements the given command name, then the method will return the function object of that method.
        Args:
            command_name: The command name to which the method/ function object is requested

        Returns:
        The function object of the internal command context method with the name specified by the command name
        """
        try:
            command_method_name = self.assemble_command_name(command_name)
            return getattr(self, command_method_name)
        except AttributeError as attribute_error:
            raise attribute_error

    @staticmethod
    def assemble_command_name(command_name):
        """
        Using the name of the command specified by 'command_name' to assemble the name of the method of the context
        object corresponding to that command name. By definition the names of the methods corresponding to specific
        commands have to be named beginning with command, followed by an underscore and the the actual command name
        Notes:
            This method will only assemble the string, as defined by definition, but will not check for the validity
            of that string. The command specified by the command name, might not even be subject to the specific
            command context object, but the possible name will be assembled anyways.
        Args:
            command_name: The string command name of the command for which the method name is requested

        Returns:
        The string name of the CommandContext method corresponding to the command name given
        """
        string_list = ["command_", command_name]
        command_method_name = ''.join(string_list)
        return command_method_name


class CommandingForm:
    """
    INTERFACE
    """
    def __init__(self, form):
        self.form = form
        # The spec dict contains all the key value pairs specified in the body 
        self.spec = self.procure_body_dict_raw()

    def build_form(self):
        """
        This method will be used by all the subclasses to create a form object, that represents the information of
        the specialized commanding form, in the case, that the subclasses are not created by passing them a form upon
        which they are based, but rather the more specific parameter set, that describes their behaviour.
        Although for this to work, the sub classes of this class have to implement methods, that create and return the
        body list of strings and the appendix data structure from their individual data set.
        Returns:
        The form object, that was created as a representation of the complex and specialized data set describing an
        individual sub class of this base class form representation
        """
        title = self.procure_form_title()
        body = self.procure_form_body()
        appendix = self.procure_form_appendix()
        form = Form(title, body, appendix)
        return form

    def procure_form_title(self):
        """
        This method creates the title of the form, that is supposed to represent the subclasses of the CommandingForm.
        The title is per protocol defined as the type of the object, which is a upper case noun briefly describing
        the purpose of the class
        Returns:
        The string of the title of the form to be created from the object, which is the type string of the class
        """
        return self.type

    def procure_form_body(self):
        """
        HAS TO BE OVERWRITTEN BY SUB CLASS
        This method will have to create and return a list of strings, that describes the body lines of a form object,
        that represent the subclass.
        Returns:
        The list of strings for the body lines of the form to be created from the data of the sub class object
        """
        raise NotImplementedError("This method has to be overwritten by the sub class!")

    def procure_form_appendix(self):
        """
        HAS TO BE OVERWRITTEN BY SUB CLASS
        This method will have to create and return a data structure, that can be assignes as the appendix of a form and
        that per protocol defines the sub class creating it as that form.
        Returns:
        The appendix data structure
        """
        raise NotImplementedError("This method has to be overwritten by the sub class!")

    def procure_body_dict_raw(self):
        """
        This method will return a dictionary, which has one entry for every line in the body string, whose key is the
        sub string before the split character ':' has occurred and the value being the substring after that character.
        Returns:
        The dictionary which assignes string keys to string values
        """
        body_dict = {}
        # Getting the list of split lists of the body string
        body_list_split = self.procure_body_lines_split()
        for line_list in body_list_split:
            body_dict[line_list[0]] = line_list[1]
        return body_dict

    def procure_body_lines_split(self):
        """
        This method returns a list of lists, with one sub list for each line in the body string. The sub lists are the
        split lists of the lines by the ':' character and each sub list therefore contains two strings.
        Raises:
            ValueError: In case the formatting of the form is wrong and there is either no ':' or more than one in
                a line
        Returns:
        A list of lists, where each sub list has two string items
        """
        body_lines = self.body.split()
        body_lines_split = []
        for line in body_lines:
            split_line = line.split(":")
            # In case the line does not have exactly one ':' character raising error, because invalid format
            if len(split_line) != 2:
                raise ValueError("The CommandingProtocol dictates, that there is exactly one ':' per line in body!")
            body_lines_split.append(split_line)
        return body_lines_split

    def procure_body_lines(self):
        """
        This method will return a list os strings, where each string is one line of the body string. A line is defined
        as the sum if characters until a new line character.
        Returns:
        The list of line strings for the body
        """
        body_lines = self.body.split("\n")
        return body_lines

    def check_spec_key(self, key):
        """
        This method checks if there is a key of the given name in the spec dictionary. In case the key is not part of
        the dict, an error will be risen.
        Raises:
            AttributeError
        Args:
            key: The string name of the key to be in the spec dictionary and therefore in the body of the form

        Returns:
        void
        """
        if key not in self.spec.keys():
            raise AttributeError("The key {} was not specified in the body of the form".format(key))

    def check_type(self):
        """
        This method will check if the type of the object matches the type of the form, upon which it is based on
        Returns:
        void
        """
        if self.title != self.type:
            raise TypeError("The form is not fit for a {} form type wrap object!".format(self.type))

    @property
    def type(self):
        """
        This method will return the type of the command form subclass. The functionality is purely based on the naming
        convention of the CommandingForm subclasses, which has to be the type of the form followed by 'Form'. The
        string of the type will then be returned as all upper case.
        Examples:
            If the type of the object would for example be Apple, then per naming convention the subclass would be
            named 'AppleForm', this class would then return the string 'APPLE', which was extracted from the class name
        Returns:
        The upper case string of the type of the subclass
        """
        # Getting the class name and removing the Form at the end
        class_name = self.__class__.__name__
        type_name = class_name.replace("Form", "")
        # Making it upper case and then returning it
        return type_name.upper()

    @property
    def title(self):
        """
        This method is the property getter for the title of the form. It will return the title of the wrapped form
        Returns:
        the string title of the form
        """
        return self.form.title

    @property
    def body(self):
        """
        This method is the property getter for the body of the form. It will return the body of the wrapped form
        Returns:
        The string of the body of the form
        """
        return self.form.body

    @property
    def appendix(self):
        """
        This is the property getter if the appendix object of the form. It will return the appendix of the wrapped form
        Returns:
        The appendix object of the wrapped form
        """
        return self.form.appendix

    @property
    def appendix_encoder(self):
        """
        This is the property getter method of the encoder object, that is responsible for the encoding and decoding
        of the form object. It will simply return the encoder of the wrappped form
        Returns:
        The AppendixEncoder form, with which the form is being made network transmittable
        """
        return self.form.appendix_encoder

    @staticmethod
    def assemble_body_line(key, value):
        """
        This method assembles the key and value strings for a line in the body of the form, by joining them with a
        ':' used as separator
        Args:
            key:
            value:

        Returns:

        """
        body_line = ':'.join([key, value])
        return body_line


class CommandForm(CommandingForm):

    def __init__(self, command, pos_args=[], kw_args={}, return_handle="reply", error_handle="reply"):
        # Initializing the attributes for the command form
        if isinstance(command, Form):
            CommandingForm.__init__(self, command)
            self.check_type()
            # Loading the data from the form
            self.command_name = self.procure_command_name()
            self.pos_args = self.procure_positional_args()
            self.key_args = self.procure_keyword_args()
            self.error_handle = self.procure_error_handle()
            self.return_handle = self.procure_return_handle()
        elif isinstance(command, str):
            # The string name of the command to be called in the remote location
            self.command_name = command
            # The positional arguments for the command call
            self.pos_args = pos_args
            # The keyword arguments for the command call
            self.key_args = kw_args
            # The handles are string identifiers about how the return value and the error are suppose to be treated
            self.error_handle = error_handle
            self.return_handle = return_handle
            # Building the form from the information about the command
            form = self.build_form()
            CommandingForm.__init__(self, form)

    def procure_form_appendix(self):
        """
        This method will create the appendix dictionary for the form based on what psoitional and kw arguments have
        been passed to the CommandForm object
        Returns:
        The dictionary, containing the pos and kw args for the command call
        """
        return {"pos_args": self.pos_args, "kw_args": self.key_args}

    def procure_form_body(self):
        """
        This method first creates the spec dictionary from the data about the command stored in the attributes of the
        object, that means about the command name, the return and error mode and the amount of pos args. The it
        assembles this dictionary into the actual body string list
        Returns:
        The list of strings, which are supposed to be the lines of the body string of a form
        """
        string_list = []
        # Getting the spec of the form on which to base the body string
        spec = self.procure_form_spec()
        # Making a new line for each dictionary entry
        for key, value in spec.items():
            line_string = ':'.join([key, value])
            string_list.append(line_string)
        # Appending all the lines to a body, separated by newline characters
        return string_list

    def procure_form_spec(self):
        """
        This method assembled the spec dictionary from the data given for the command form
        Returns:
        the dictionary with the string key value pairs for a command form
        """
        spec = dict()
        spec["error"] = self.error_handle
        spec["return"] = self.return_handle
        spec["command"] = self.command_name
        spec["pos_args"] = str(len(self.pos_args))
        return spec

    def procure_return_handle(self):
        """
        This method will get the return handle string from the spec dict
        Returns:
        the string return handle
        """
        self.check_return_handle()
        return_handle = self.spec["return"]
        return return_handle

    def procure_error_handle(self):
        """
        This method will get the error handle from the spec dict
        Returns:
        The string error handle identifier
        """
        self.check_error_handle()
        error_handle = self.spec["error"]
        return error_handle

    def procure_positional_args(self):
        """
        This method gets the positional arguments list from the appendix dict
        Returns:
        the list of positional arguments for the command call
        """
        self.check_pos_args()
        pos_args = self.appendix["pos_args"]
        if not isinstance(pos_args, list):
            raise TypeError("The positional arguments are supposed to be list!")
        return pos_args

    def procure_keyword_args(self):
        """
        This method gets the key word argument dict from the appendix dict of the form
        Returns:
        The dictionary, that specifies the kewword arguments for the command call
        """
        kw_args = self.appendix["kw_args"]
        if not isinstance(kw_args, dict):
            raise TypeError("The keyword arguments are supposed to be dict!")
        return kw_args

    def procure_command_name(self):
        """
        This method gets the command name for the command to be issued/represented by this form from the spec dict,
        which is based on the information in the body of the form.
        Returns:

        """
        # Checking for the existence of the command name in the spec of the body; raises AttributeError if not
        self.check_command_name()
        # Getting the command name from the dict and returning it
        command_name = self.spec["command"].strip()
        return command_name

    def check_appendix(self):
        """
        This method checks if the appendix object of the form is a dictionary and if that dict has the two entries for
        the pos args and the kw args, as it has to be with a command form
        Returns:
        void
        """
        # Checking if the appendix even is a dictionary
        dict_type = not isinstance(self.appendix, dict)
        if dict_type:
            raise TypeError("The appendix of the command form is supposed ot be a dict!")
        # Checking if the entries of the appendix dict are correct
        keys = self.appendix.keys()
        entries = len(keys) != 2 or 'pos_args' not in keys() or 'kw_args' not in keys()
        if entries:
            raise KeyError("The entries of form appendix do not match command form!")

    def check_command_name(self):
        """
        This method checks if the 'command' field was specified in the body of the form and raises an error if that is
        not the case
        Raises:
            AttributeError: In case the key 'command' is not in the spec dict
        Returns:
        void
        """
        self.check_spec_key("command")

    def check_pos_args(self):
        """
        This method checks if the spec dictionary, which is based on the form body contains an entry, that is named
        'pos_args', which is supposed to be a int number for the amount of pos args to be given to the command call.
        Also checks the conversion.
        Raises:
            AttributeError: in case the entry is not even in the spec dict
            TypeError: In case the value to the entry is not int convertable
        Returns:
        void
        """
        self.check_spec_key("pos_args")
        try:
            int(self.spec["pos_args"].strip())
        except ValueError:
            raise TypeError("The pos_args entry is supposed to be integer type convertable")

    def check_error_handle(self):
        """
        This method checks if the spec dictionary, which is based in the body string of the form, contains an entry
        about the error handle of the command call.
        Returns:
        void
        """
        self.check_spec_key("error")

    def check_return_handle(self):
        """
        This method checks if the spec dictionary, which is based on the body string of the form, contaisn an entry
        about the return handle of the command call.
        Returns:
        void
        """
        self.check_spec_key("return")


class ReturnForm(CommandingForm):

    def __init__(self, return_value):
        if isinstance(return_value, Form):
            CommandingForm.__init__(self, return_value)
            self.check_type()
            self.return_value = self.procure_return_value()
        else:
            self.return_value = return_value
            self.return_type = self.procure_return_type_string()
            form = self.build_form()
            CommandingForm.__init__(self, form)

    def procure_form_body(self):
        """
        This method creates the form body list with one entry and that being the string of the return type
        Returns:
        The list with the body string lines
        """
        body_string = ':'.join(["type", self.return_type])
        return [body_string]

    def procure_form_appendix(self):
        """
        This method creates a dictionary with one entry being the return value of this object
        Returns:
        The assembled dictionary as the appendix of the form
        """
        return {"return": self.return_value}

    def procure_return_value(self):
        """
        This method will extract the return value from the underlying form. The return value object is supposed to be
        stored in the entry with the key 'return'
        Returns:
        The object which is supposed to be the return
        """
        self.check_appendix()
        return_value = self.appendix["return"]
        return return_value

    def procure_return_type_string(self):
        """
        This method will get the string format of the type of the return value
        Returns:
        The string of the type of the return value object
        """
        return_type = self.procure_return_type()
        return str(return_type)

    def procure_return_type(self):
        """
        This method will get the type of the return value of the return form object
        Returns:
        The type object for the type of the return form object
        """
        return_type = type(self.return_value)
        return return_type

    def check_appendix(self):
        """
        This method checks if the appendix of the given form is actually a dictionary object and if that dictionary
        contains an entry with the key "return" as it should do
        Raises:
            TypeError: In case the dictionary is not how it should be
        Returns:
        void
        """
        if not isinstance(self.appendix, dict) or 'return' not in self.appendix.keys():
            raise TypeError("The appendix has to be a dict!")


class ErrorForm(CommandingForm):

    def __init__(self, exception):
        if isinstance(exception, Exception):
            self.exception = exception
            form = self.build_form()
            CommandingForm.__init__(self, form)
        elif isinstance(exception, Form):
            CommandingForm.__init__(self, exception)
            self.check_type()
            self.exception = self.procure_exception()
        else:
            raise TypeError("The Error form has to be passed either form or exception object!")

    def procure_form_appendix(self):
        """
        This method will create the appendix of the form, which is supposed to represent this object. If the
        appendix encoder used for the form is able to encode the exception object itself a dictionary will be sent,
        that only has ine item with the key 'error' and tge value being the exception object. If the encoder is not
        able to serialize the exception, an empty dict will be used as appendix
        Returns:
        dict
        """
        if self.appendix_encoder.is_serializable(self.exception):
            return {"error": self.exception}
        else:
            return {}

    def procure_form_body(self):
        """
        This method will create the body of a form, which is supposed to represent this object, from the exception
        name of the exception, that was passed to the object for construction.
        Returns:
        The list containing
        """
        # Getting the name of the exception
        exception_name = self.procure_exception_name()
        exception_message = self.procure_exception_message().replace("\n", "")
        name_line = self.assemble_body_line("name", exception_name)
        message_line = self.assemble_body_line("message", exception_message)
        return [name_line, message_line]

    def procure_exception_name(self):
        """
        This method extracts the exception name from the exception attribute of this class and then returns the string
        name of the exception class
        Returns:
        The string name of the exception
        """
        exception_class = self.exception.__class__
        exception_name = exception_class.__name__
        return exception_name

    def procure_exception_message(self):
        """
        This method will get the exception message from the exception object, that is the attribute of this object
        Returns:
        The string exception message
        """
        exception_message = str(self.exception)
        return exception_message

    def procure_exception(self):
        """
        This method will create an exception object from the data given by the underlying form object. In case there is
        only an empty appendix (which means that the appendix encoder cannot encode exception objects) a new exception
        object will be created by dynamically interpreting the error name and message in the body of the form. In case
        there is an appendix using the exception object stored in the appendix to return
        Returns:
        An exception object, as specified by the form
        """
        if len(self.appendix) == 0:
            # Creating the python expression of creating a new exception object as a string expression from the name
            # and message of the exception from the body
            eval_string = self.procure_exception_eval_string()
            # Dynamically interpreting that string and retunring the new exception object
            return eval(eval_string)
        else:
            return self.appendix["error"]

    def procure_exception_eval_string(self):
        """
        This method will create a string expression, that represents a python source code statement of creating a new
        exception object with using the excepetion name, specified by the body as the class to create and the message
        given in the body as the string parameter for the exception object creation.
        Returns:
        A string, that is a python statement
        """
        exception_name = self.spec["name"]
        exception_message = self.spec["message"]
        return ''.join([exception_name, "('", exception_message, "')"])


class CommandingBase(threading.Thread):

    def __init__(self, connection, separation="$separation$"):
        self.connection = connection
        self.separation = separation

    def wait_request(self):
        """
        This method waits an indefinite amount of time for a new line to be received over the connection, then checks
        if the received string is a 'request' string. In case it is, an 'ack' string will be sent back to the client,
        which signals, that the actual form can now be transmitted.
        Returns:
        void
        """
        # Waiting for a line to be received by the connection
        line_string = self.wait_line()
        if line_string != "request":
            raise ValueError("The client has sent wrong request identifier")
        # Sending the ack in response
        self.send_ack()

    def send_ack(self):
        """
        This method will send the string 'ack' over the connection object followed by a new line character. An ack is
        being sent as the response to a request by the client of the connection and thus also signals the client to
        begin sending the actual form.
        Returns:
        void
        """
        self.connection.sendall_string("ack\n")

    def wait_line(self):
        """
        This method will wait an indefinite amount of time until a string is being sent over a the connection and will
        then eventually return the substring until a new line character has occurred in the stream
        Returns:
        The received string
        """
        return self.connection.wait_string_until_character("\n")

    def send_command_context_type(self):
        """
        This method will send the string representation of the command context class, so that on the remote side of the
        communication it can be compared, if the server and client are on the same page
        Returns:

        """
        command_context_type_string = str(self.command_context_class)
        self.connection.sendall_string(command_context_type_string)

    @property
    def command_context_class(self):
        """
        Both the client and the server are supposed to implement a property for getting the type of the command context
        object, which they are based on. This function is supposed to return the class specification of the command
        context object
        Returns:
        The class object of the respective command contect, on which the object is based on
        """
        raise NotImplementedError()

    @staticmethod
    def evaluate_commanding_form(form):
        """
        This is a utility function, which evaluates a form object, as it was received by the form transmission
        protocol and returns the commanding form wrapper object according to what the original form is meant to
        resemble.
        Raises:
            TypeError: In case the passed value is not Form object
            ValueError: In case the type of the form is none of the commanding forms command, return or error
        Args:
            form: The form to be wrapped in a commanding form

        Returns:
        The commanding form, the given form is meant to resemble
        """
        if not isinstance(form, Form):
            raise TypeError("Only Form objects can be evaluated to CommandingForm objects")
        if form.title == "COMMAND":
            return CommandForm(form)
        elif form.title == "RETURN":
            return ReturnForm(form)
        elif form.title == "ERROR":
            return ErrorForm(form)
        else:
            raise ValueError("The received form '{}' is not a commanding form")



class CommandingHandler(CommandingBase):

    def __init__(self, connection, command_context):
        # Initializing the super class
        CommandingBase.__init__(connection)

        self.command_context = command_context

        # Setting the running state variable to True
        self.running = True

    def run(self):

        while True:
            try:

                self.validate()
                while True:
                    self.wait_request()
                    receiver = FormReceiverThread(self.connection, self.separation)
                    receiver.start()
                    form = receiver.receive_form()


            except ConnectionAbortedError as connection_aborted:
                # This is the case if the type of command contexts does not match between server and client
                pass

            except ConnectionError as connection_error:
                pass

    def execute_form(self, form):
        """
        This method will execute the form with the command context object on which it is based on
        Args:
            form: The received Form object

        Returns:

        """
        self.command_context.execute_form(form)

    def validate(self):
        """
        This method checks, if the server and the client have the same command context to work with
        Returns:
        void
        """
        # Sending the type of command context in which the server is based on to the client
        self.send_command_context_type()
        # Receiving the type of command context on which the client is based on from the client
        client_command_context = self.connection.receive_line()
        if str(self.command_context_class) != client_command_context:
            raise ConnectionAbortedError("The client and server do not have the same command context")

    def _check_command_context(self):
        """
        This method checks if the object passed to specify the command context is actually a CommandContext object
        Returns:
        void
        """
        if not isinstance(self.command_context, CommandContext):
            raise TypeError("The command context parameter of the Commanding server has to be CommandContext")

    @property
    def command_context_class(self):
        """
        This function returns the class object of the command context object, on which the server is based on
        Returns:
        The class object
        """
        return self.command_context.__class__
