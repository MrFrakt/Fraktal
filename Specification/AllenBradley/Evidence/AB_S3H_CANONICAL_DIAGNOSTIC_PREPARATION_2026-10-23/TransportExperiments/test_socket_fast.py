import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pylogix.lgx_comm import Connection
import socket_fast as reads

REQ=b'\x52\x03\x91\x04Root'+struct.pack('<HI',1,0)


class Socket:
    def __init__(self,chunk=65536,send_chunk=65536,corrupt=None):
        self.chunk=chunk;self.send_chunk=send_chunk;self.corrupt=corrupt;self.input=bytearray();self.output=bytearray()
        self.timeout=3;self.closed=False;self.pending=0;self.maximumPending=0
    def gettimeout(self):return self.timeout
    def settimeout(self,value):self.timeout=value
    def setblocking(self,value):self.timeout=None if value else 0
    def send(self,data):
        size=min(len(data),self.send_chunk);self.input.extend(data[:size])
        if len(self.input)>=24 and len(self.input)==24+struct.unpack_from('<H',self.input,2)[0]:
            if self.pending:raise AssertionError('more than one pending request')
            self.pending+=1;self.maximumPending=max(self.pending,self.maximumPending)
            tx=bytes(self.input);self.input.clear();body=b'\xd2\0\x06\0\xa0\x02\x34\x12'+tx[44:46]
            rx=bytearray(tx[:46]+body);struct.pack_into('<H',rx,2,len(rx)-24);struct.pack_into('<H',rx,42,len(body)+2)
            if self.corrupt:self.corrupt(rx)
            self.output.extend(rx)
        return size
    def recv(self,size):
        part=bytes(self.output[:min(size,self.chunk)]);del self.output[:len(part)]
        if not self.output:self.pending=0
        return part
    def close(self):self.closed=True


def ready(waiting,sending,errors,timeout):return [s for s in waiting if s.output],sending,[]


class SocketReadTests(unittest.TestCase):
    def channels(self,**options):
        result=[]
        for i in range(4):
            c=Connection(SimpleNamespace());c.Socket.close();c.msg_socket.close();c.Socket=Socket(**options)
            c.SocketConnected=c._connected=c._registered=True;c._session_handle=123+i;c._ot_connection_id=456+i
            result.append(SimpleNamespace(ConnectionSize=4000,conn=c))
        return result
    def plans(self):return [[dict(kind='fragment',request=REQ) for _ in range(n)] for n in (12,12,12,11)]

    def test_four_owned_sockets_preserve_47_replies_and_restore_timeouts(self):
        for chunk in (1,23,54,65536):
            cs=self.channels(chunk=chunk,send_chunk=7)
            with patch.object(reads.select,'select',side_effect=ready):results=reads.acquire(cs,self.plans())
            self.assertEqual([len(rows) for rows in results],[12,12,12,11])
            for c,rows in zip(cs,results,strict=True):
                self.assertEqual([struct.unpack_from('<H',r,44)[0] for s,r in rows],list(range(1,len(rows)+1)))
                self.assertTrue(all(s==6 for s,r in rows));self.assertEqual(c.conn.Socket.timeout,3)
                self.assertEqual(c.conn.Socket.maximumPending,1);self.assertFalse(c.conn.Socket.output)

    def test_response_identity_error_closes_every_connection_without_retry(self):
        def corrupt(raw):raw[44]^=1
        cs=self.channels(corrupt=corrupt)
        with patch.object(reads.select,'select',side_effect=ready),self.assertRaises(ValueError):reads.acquire(cs,self.plans())
        self.assertTrue(all(c.conn.Socket.closed and not c.conn.SocketConnected for c in cs))

    def test_only_reads_distinct_sockets_and_bounded_connection_count(self):
        cs=self.channels();plans=self.plans();plans[0][0]['request']=b'\x4d'+REQ[1:]
        with self.assertRaises(ValueError):reads.acquire(cs,plans)
        self.assertTrue(all(c.conn._sequence_counter==1 for c in cs))
        with self.assertRaises(ValueError):reads.acquire([cs[0]]*4,self.plans())
        with self.assertRaises(ValueError):reads.acquire(cs+[cs[0]],self.plans()+[self.plans()[0]])

    def test_socket_timeout_and_early_eof_fail_closed(self):
        cs=self.channels()
        with patch.object(reads.select,'select',side_effect=TimeoutError('test')),self.assertRaises(TimeoutError):reads.acquire(cs,self.plans())
        self.assertTrue(all(c.conn.Socket.closed for c in cs))
        cs=self.channels();cs[0].conn.Socket.recv=lambda size:b''
        with patch.object(reads.select,'select',side_effect=ready),self.assertRaises(OSError):reads.acquire(cs,self.plans())
        self.assertTrue(all(c.conn.Socket.closed for c in cs))


if __name__=='__main__':unittest.main()
