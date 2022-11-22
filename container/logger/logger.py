#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import time
import json
import subprocess
import os
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

registrydir = "/var/lib/registry"

# Init Logger
log = logging.getLogger('LOGGER')
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

class RequestHandler(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_HEAD(self):

        self._set_headers()

        return True

    def do_GET(self):

        request_path = self.path

        # print("\n----- Request Start ----->\n")
        # print(request_path)
        # print(self.headers)
        # print("<----- Request End -----\n")

        self._set_headers()

        self.wfile.write("<html><head><titleDocker Registry Notifications</title></head>".encode("utf-8"))
        self.wfile.write("<body><b>BaseHTTPServer for Docker Registry Notifications.</b><br><i>The server sends a message when the image pushed to private docker registry.</i>".encode("utf-8"))
        self.wfile.write("<br><br>".encode("utf-8"))
        self.wfile.write("<a href='https://docs.docker.com/registry/configuration/'>Docker registry configuration</a><br>".encode("utf-8"))
        self.wfile.write("<a href='https://docs.docker.com/registry/notifications'>Docker registry notifications</a><br>".encode("utf-8"))
        self.wfile.write("<a href='https://docs.python.org/3/library/http.server.html'>Python 3 HTTP servers</a><br>".encode("utf-8"))
        self.wfile.write("<br><hr>".encode("utf-8"))
        self.wfile.write(("You accessed Request: <b>%s</b>" % request_path).encode("utf-8"))
        self.wfile.write("</body></html>".encode("utf-8"))

        return True


    def do_POST(self):

        request_path = self.path
        #request_path_parse = url_to_dict(request_path)
        #hook = str(request_path_parse['hook'])

        request_headers = self.headers
        # content_length = request_headers.getheaders('content-length')
        content_length = request_headers.get_all('content-length', 0)
        content_length_check = int(content_length[0]) if content_length else 0

        content_body = self.rfile.read(content_length_check)
        content_body_json = json.loads(content_body)

        # print("\n----- Request Start ----->\n")
        # print('Request: ' + request_path)
        # print(request_headers)
        # print(content_body)
        # print("<----- Request End -----\n")

        self._set_headers()

        if content_body_json:

            # print(json.dumps(content_body_json, indent=4))

            # repository = content_body_json['events'][0]['target']['repository']
            # url = content_body_json['events'][0]['target']['url']
            # mediaType = content_body_json['events'][0]['target']['mediaType']
            #
            # try:
            #     tag = content_body_json['events'][0]['target']['tag']
            #
            # except KeyError:
            #     tag = None
            #
            digest = content_body_json['events'][0]['target']['digest']
            # timestamp = content_body_json['events'][0]['timestamp']
            # try:
            #   actor = content_body_json['events'][0]['actor']['name']
            # except:
            #   actor = "actor-manu"
            # action = content_body_json['events'][0]['action']

            # print(repository, url, mediaType, tag,
            #       digest, timestamp, actor, action)



        # Update atime of requested blob
        log.info("Digest request: " + digest)
        updateatimedigest(digest)


        # Checking if blob is a json and return None if not
        digestblobjson = getjson(digest)

        # Loop in layers and update atime of layer blobs
        if digestblobjson is not None and 'layers' in digestblobjson.keys():
            log.debug("Searching for layers...")
            for layer in digestblobjson['layers']:
              log.debug("Layer found: " + layer['digest'])
              updateatimedigest(layer['digest'])


def getjson(digest):
    digestarray = digest.split(":")
    digesthash = digestarray[1]
    blobfile = registrydir + '/docker/registry/v2/blobs/sha256/' + digesthash[:2] + '/' + digesthash + '/data'
    if os.path.exists(blobfile):
        f = open(blobfile,'r')
        try:
            blobjson = json.load(f)
            isJson = True
        except:
            log.debug("Layer blob is not json ")
            isJson = False
        f.close()
        if isJson:
            return blobjson
        else:
            return None;

def updateatimedigest(digest):

  digestarray = digest.split(":")
  digesthash = digestarray[1]
  blobfile = registrydir + '/docker/registry/v2/blobs/sha256/' + digesthash[:2] + '/' + digesthash + '/data'

  if os.path.exists(blobfile):
    log.info("Updating access time of digest: " + digest )
    log.debug("Updating access time of file: " + blobfile)
    os.utime(blobfile)


def url_to_dict(url):

    url_dict = dict()

    for item in url.split("&"):
        item = item.replace("/", "")
        item = item.replace("?", "")
        url_dict[item.split("=")[0]] = item.split("=")[1]

    return url_dict


def main(server_class=HTTPServer, handler_class=RequestHandler, server='0.0.0.0', port=8000):

    server_address = (server, port)
    httpd = server_class(server_address, handler_class)
    log.info("Server Starts - %s:%s" %
          (server, port))

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()
    log.info("Server Stops - %s:%s" %
          (server, port))

    return True


if __name__ == '__main__':

    if len(sys.argv) == 2:
        sys.exit(main(port=int(sys.argv[1])))
    else:
        sys.exit(main())
