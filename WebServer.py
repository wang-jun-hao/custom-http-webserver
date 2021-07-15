import sys
from socket import *


def processHeader(headerInString):
    substrings = headerInString.split(" ")
    length = len(substrings)
    method = substrings[0].upper()
    path = substrings[1]
    contentLength = 0

    if method == "POST":
        for i in range(2, length - 1, 2):
            if substrings[i].upper() == "CONTENT-LENGTH":
                contentLength = int(substrings[i + 1])

    return method, path, contentLength


def processPath(path):
    subPaths = path.split("/")
    storeType = subPaths[1]
    key = subPaths[2]

    return storeType, key


def processKeyRetrieval(key, keyStore, counterStore):
    if key not in keyStore:
        return "404 NotFound", b''
    else:  # key in keyStore
        value = keyStore[key]
        length = len(value)

        if key in counterStore:
            currCount = counterStore[key]
            currCount -= 1

            counterStore[key] = currCount

            if currCount == 0:
                del counterStore[key]
                del keyStore[key]

        return "200 OK Content-Length " + str(length), value


def processKeyDeletion(key, keyStore, counterStore):
    if key not in keyStore:
        return "404 NotFound", b''
    else:  # key in keyStore
        if key in counterStore:
            return "405 MethodNotAllowed", b''
        else:
            value = keyStore[key]
            length = len(value)

            del keyStore[key]

            return "200 OK Content-Length " + str(length), value


def processKeyInsertUpdate(key, value, keyStore, counterStore):
    if key not in keyStore:  # insertion
        keyStore[key] = value
        return "200 OK", b''
    else:  # update
        if key in counterStore:
            return "405 MethodNotAllowed", b''
        else:  # key not in counterStore
            keyStore[key] = value
            return "200 OK", b''


def processCounterRetrieval(key, keyStore, counterStore):
    if key not in keyStore:
        return "404 NotFound", b''
    else:  # key in keyStore
        if key in counterStore:
            countValue = counterStore[key]

            return "200 OK Content-Length 1", str(countValue).encode()
        else:  # key not in counterStore
            return "200 OK Content-Length 8", b'Infinity'


def processCounterDeletion(key, counterStore):
    if key not in counterStore:
        return "404 NotFound", b''
    else:  # key in counterStore
        countValue = counterStore[key]

        del counterStore[key]

        return "200 OK Content-Length 1", str(countValue).encode()


def processCounterInsertIncre(key, value, keyStore, counterStore):
    if key not in keyStore:
        return "405 MethodNotAllowed", b''
    else:  # key in keyStore
        if key not in counterStore:
            counterStore[key] = int(value.decode())

            return "200 OK", b''
        else:  # key in counterStore
            countValue = counterStore[key]

            countValue += int(value.decode())

            counterStore[key] = countValue

            return "200 OK", b''


def processRequest(method, storeType, key, value, keyStore, counterStore):
    if method == "GET":
        if storeType == "key":
            return processKeyRetrieval(key, keyStore, counterStore)
        else:
            return processCounterRetrieval(key, keyStore, counterStore)
    elif method == "DELETE":
        if storeType == "key":
            return processKeyDeletion(key, keyStore, counterStore)
        else:
            return processCounterDeletion(key, counterStore)
    else:  # method is POST
        if storeType == "key":
            return processKeyInsertUpdate(key, value, keyStore, counterStore)
        else:
            return processCounterInsertIncre(key, value, keyStore, counterStore)


serverPort = int(sys.argv[1])

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)

keyStore = dict()
counterStore = dict()

while True:
    connectionSocket, address = serverSocket.accept()
    byteChunkBuffer = b''
    keepAlive = True


    while keepAlive:
        pos = byteChunkBuffer.find(b'  ')

        while pos < 0:
            byteChunk = connectionSocket.recv(1024)

            if len(byteChunk) == 0:
                keepAlive = False
                break

            byteChunkBuffer += byteChunk

            pos = byteChunkBuffer.find(b'  ')

        # complete header received -> look for Content-Length

        if not keepAlive:
            break

        headerOfCurrPacketInBytes = byteChunkBuffer[0: pos]  # header without double space at the end
        byteChunkBuffer = byteChunkBuffer[pos+2:]  # remaining data in buffer
        # double space is discarded from sequence

        headerOfCurrPacketInString = headerOfCurrPacketInBytes.decode()

        method, path, contentLength = processHeader(headerOfCurrPacketInString)
        storeType, key = processPath(path)

        while len(byteChunkBuffer) < contentLength:
            byteChunk = connectionSocket.recv(1024)
            byteChunkBuffer += byteChunk

        # full packet data is in buffer now

        value = byteChunkBuffer[0: contentLength]
        byteChunkBuffer = byteChunkBuffer[contentLength:]

        responseHeader, contentBody = processRequest(method, storeType, key, value, keyStore, counterStore)

        responseHeader = responseHeader + "  "

        responseInBytes = responseHeader.encode() + contentBody

        connectionSocket.send(responseInBytes)

    connectionSocket.close()
