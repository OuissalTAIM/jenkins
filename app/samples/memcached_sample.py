# -*- coding: utf-8 -*-


from pymemcache.client import base


if __name__ == "__main__":
    client = base.Client(('localhost', 11211))
    client.set('name', 'jesa app')
    print(client.get('name'))