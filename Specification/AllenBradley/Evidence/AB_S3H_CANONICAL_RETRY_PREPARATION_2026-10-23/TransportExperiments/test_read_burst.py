import struct
from types import SimpleNamespace
import unittest
from pylogix.lgx_comm import Connection
import read_burst as burst


def request():return b'\x52\x03\x91\x04Root'+struct.pack('<HI',1,0)


class Socket:
    def __init__(self,*,chunk=65536,reverse=False,corrupt=None):
        self.chunk=chunk;self.reverse=reverse;self.corrupt=corrupt;self.buffer=bytearray();self.sends=[];self.closed=False
    def sendall(self,raw):
        frames=[];remaining=raw
        while remaining:
            length=struct.unpack_from('<H',remaining,2)[0]+24;tx=remaining[:length];remaining=remaining[length:]
            data=b'\xd2\x00\x06\x00\xa0\x02\x34\x12'+tx[44:46]
            rx=bytearray(tx[:46]+data);struct.pack_into('<H',rx,2,len(rx)-24);struct.pack_into('<H',rx,42,len(data)+2)
            if self.corrupt:self.corrupt(rx)
            frames.append(bytes(rx))
        self.sends.append(len(frames));self.buffer.extend(b''.join(reversed(frames) if self.reverse else frames))
    def recv(self,size):
        part=bytes(self.buffer[:min(size,self.chunk)]);del self.buffer[:len(part)];return part
    def close(self):self.closed=True


class BurstTests(unittest.TestCase):
    def comm(self,**options):
        conn=Connection(SimpleNamespace());conn.Socket.close();conn.msg_socket.close()
        conn.Socket=Socket(**options);conn.SocketConnected=conn._connected=conn._registered=True
        conn._session_handle=123;conn._ot_connection_id=456
        return SimpleNamespace(ConnectionSize=4000,conn=conn)
    def items(self,n=4):return [dict(kind='fragment',request=request()) for i in range(n)]

    def test_coalesced_and_split_tcp_frames_are_exact_and_correlated(self):
        for chunk in (1,3,23,50,65536):
            comm=self.comm(chunk=chunk);result=burst.acquire(comm,self.items())
            self.assertEqual([s for s,r in result],[6]*4)
            self.assertEqual([struct.unpack_from('<H',r,44)[0] for s,r in result],[1,2,3,4])
            self.assertFalse(comm.conn.Socket.closed)

    def test_reply_order_is_bound_by_session_context_and_sequence(self):
        comm=self.comm(reverse=True);result=burst.acquire(comm,self.items())
        self.assertEqual([struct.unpack_from('<H',r,44)[0] for s,r in result],[1,2,3,4])

    def test_pending_window_is_bounded_and_all_responses_drain(self):
        comm=self.comm();result=burst.acquire(comm,self.items(35))
        self.assertEqual(comm.conn.Socket.sends,[16,16,3]);self.assertEqual(len(result),35)
        self.assertFalse(comm.conn.Socket.buffer)

    def test_write_nested_write_and_object_service_refused_before_send(self):
        for req in (b'\x4d'+request()[1:],b'\x52\x02\x20\x06\x24\x01'+b'\x01\0'+b'\0'*4,
                    b'\x0a\x02\x20\x02\x24\x01\x01\0\x04\0'+b'\x4d'+request()[1:]):
            comm=self.comm()
            with self.assertRaises(ValueError):burst.acquire(comm,[dict(kind='fragment',request=req)])
            self.assertEqual(comm.conn.Socket.sends,[])

    def test_changed_identity_and_bad_headers_close_connection_without_retry(self):
        for offset in (0,4,8,12,20,24,30,32,40,42,44):
            def corrupt(raw,offset=offset):raw[offset]^=1
            comm=self.comm(corrupt=corrupt)
            with self.assertRaises(ValueError):burst.acquire(comm,self.items())
            self.assertTrue(comm.conn.Socket.closed);self.assertFalse(comm.conn.SocketConnected)
            self.assertEqual(comm.conn.Socket.sends,[4])

    def test_early_eof_closes_and_prewarm_required(self):
        comm=self.comm();comm.conn.Socket.recv=lambda size:b''
        with self.assertRaisesRegex(ValueError,'ended early'):burst.acquire(comm,self.items())
        self.assertTrue(comm.conn.Socket.closed)
        comm=self.comm();comm.conn._connected=False
        with self.assertRaisesRegex(ValueError,'prewarmed'):burst.acquire(comm,self.items())
        self.assertEqual(comm.conn.Socket.sends,[])


if __name__=='__main__':unittest.main()
