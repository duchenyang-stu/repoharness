class Node:
    def __init__(self, value):
        self.value = value
        self.next = None


class LinkedList:
    """单向链表。"""

    def __init__(self):
        self.head = None
        self.tail = None
        self._size = 0

    def append(self, value):
        node = Node(value)
        if self.tail is None:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self._size += 1

    def __iter__(self):
        node = self.head
        while node is not None:
            yield node.value
            node = node.next

    def __len__(self):
        return self._size

    def reverse(self):
        """原地反转链表，需正确维护 head 和 tail。"""
        raise NotImplementedError

    def remove(self, value):
        """删除第一个等于 value 的节点；找到并删除返回 True，否则返回 False。需正确维护 head、tail 和长度。"""
        raise NotImplementedError
