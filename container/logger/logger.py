#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import time
import json
import ujson
import subprocess
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from functools import lru_cache

registrydir = "/var/lib/registry"

executor = ThreadPoolExecutor(max_workers=10)

class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger, prefix):
        super(LoggerAdapter, self).__init__(logger, {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        return '[%s] %s' % (self.prefix, msg), kwargs

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
        # Parse the request path
        request_path = self.path
        request_path_parse = url_to_dict(request_path)
        registry = str(request_path_parse['registry'])
        log = LoggerAdapter(logh, registry)

        # Read request content and load JSON
        content_length = int(self.headers.get('Content-Length', 0))
        content_body = self.rfile.read(content_length)

        try:
            content_body_json = ujson.loads(content_body)  # Using ujson for faster JSON parsing
        except ValueError:
            log.error("Error parsing JSON body.")
            self.send_error(400, "Invalid JSON format")
            return

        # Ensure JSON contains the expected 'events' key
        if "events" not in content_body_json:
            log.error("No events in JSON body.")
            self.send_error(400, "No events in request")
            return

        # Extract details from the event to identify the image
        event = content_body_json["events"][0]
        repository = event['target']['repository']
        tag = event['target'].get('tag')
        digest = event['target']['digest']
        imagenrequested = f"{repository}:{tag}" if tag else f"{repository}@{digest}"

        # Update the access time of the main digest file
        log.info(f"Image request: {imagenrequested}")
        log.info(f"Digest request: {digest}")
        updateatimedigest(digest, log)

        # Fetch the JSON blob to retrieve layer information
        digestblobjson = getjson(digest)

        # If JSON blob has layers, process each layer in parallel
        if digestblobjson and 'layers' in digestblobjson:
            log.debug("Searching for layers...")
            layer_digests = [layer['digest'] for layer in digestblobjson['layers']]

            # Run the layer access time updates in parallel using ThreadPoolExecutor
            executor.map(lambda layer_digest: updateatimedigest(layer_digest, log), layer_digests)

        # Send HTTP response indicating the POST request was processed
        self._set_headers()
        self.wfile.write("POST request processed successfully.".encode("utf-8"))



@lru_cache(maxsize=128)
def getjson(digest):
    digestarray = digest.split(":")
    digesthash = digestarray[1]
    blobfile = os.path.join(registrydir, 'docker/registry/v2/blobs/sha256', digesthash[:2], digesthash, 'data')
    if os.path.exists(blobfile):
        with open(blobfile, 'r') as f:
            try:
                blobjson = ujson.load(f)
                return blobjson
            except ValueError:
                log.debug("Layer blob is not json")
    return None


def updateatimedigest(digest,log):

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

    log = LoggerAdapter(logh, 'global')
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

    # Init Logger
    logh = logging.getLogger('LOGGER')
    logh.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logh.addHandler(handler)

    log = LoggerAdapter(logh, "global")


    if len(sys.argv) == 2:
        sys.exit(main(port=int(sys.argv[1])))
    else:
        sys.exit(main())
