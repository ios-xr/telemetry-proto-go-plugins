#!/usr/bin/env python3

import os
import re
import sys
import errno
import subprocess
import json
import glob
import argparse

IMPORTPREFIX="github.com/ios-xr/model-driven-telemetry"
REPOROOT=os.path.basename(os.getcwd())
ABSPATHCWD=os.getcwd()
SRCDIR="staging"
TGTDIR="proto_go"
PACKAGE="^(package .*);"
MSGKEYNAME="message (.*_KEYS)"

GENGOPREFIX="{}/{}/".format(REPOROOT, TGTDIR)

def walkTree(start):
    for root, dirs, files in os.walk(start):
        yield root, dirs, files

def toCamelCase(snake_str):
    """
    Modelled on protoc-gen-go/generator/generator.go Remember to
    catch the first one too. Logical OR of regexp might have been a
    little neater.

    """
    capital_snake = re.sub("^([a-z])", lambda m: m.group(1).upper(), snake_str)
    camel_onepass = re.sub("_([a-z])", lambda m: m.group(1).upper(), capital_snake)
    camel_twopass = re.sub("([0-9][a-z])", lambda m: m.group(1).upper(), camel_onepass)
    return camel_twopass

# Known protos with issues
proto_exception_list = [
    "icpe_sdacp_cfg_sfl.proto",
    "dpm_oper_if.proto",
    "icpe_cpm_oper_sat.proto",
    "mpls_te_soft_preemption_stats.proto",
    ]
def createProtolist():
    " get list of protos in [(rootdir, tgtdir, file),...]"
    protolist = []
    for root,dirs,files in walkTree(SRCDIR):
        tgt = root.replace(SRCDIR, TGTDIR, 1)
        for f in files:
            if f not in proto_exception_list:
                protolist.append((root, tgt, f))

    return protolist

def extractPackageName(filename):
    r = re.compile(PACKAGE)
    with open(filename) as f:
        for line in f:
            m = r.search(line)
            if None != m:
                return m.group(1).replace(".","_").replace("[", "_").replace("]", "_")

def extractMsgName(filename):
    r = re.compile(MSGKEYNAME)
    with open(filename) as f:
        for line in f:
            m = r.search(line)
            if None != m:
                return m.group(1), m.group(1)[:-len("_KEYS")]
    return None, None

def generatePluginAllContent(srcfilename, tgt, f, pl):
    k, c = extractMsgName(srcfilename)
    if k is None:
        print("skiping plugin build for {}".format(f))
        return
    pkg_name = extractPackageName(srcfilename)
    pl.append((tgt, pkg_name.split(' ', 1)[1], toCamelCase(k), toCamelCase(c)))


def generatePluginGoCode(srcfilename, tgt, f):
    """
    Generate plugin main and build instrustion
    """
    pluginDir = tgt + "/plugin"
    # Make directory if it does not exist
    os.makedirs(pluginDir, exist_ok=True)
    k, c = extractMsgName(srcfilename)
    if k is None:
        print("skiping plugin build for {}".format(f))
        return

    pluginFileName = pluginDir + "/" + f.rsplit('.', 1)[0] + ".plugin.go"

    pluginContent = """
package main

import (
    . ".."
)

var PluginMsg_KEYS {}
var PluginMsg      {}
""".format(toCamelCase(k), toCamelCase(c))

    doccontent = """
//go:generate go build -buildmode=plugin -o {}/{}/plugin.so {}/{}

""".format(ABSPATHCWD, pluginDir, ABSPATHCWD, pluginFileName)

    with open(pluginFileName, "w") as f:
        f.write(doccontent)
        f.write(pluginContent)

def extractRelativePath(src, tgt):
    """
    When at src, rooted from same place as tgt, get relative path to
    target. Implementation looks esoteric.

    """
    seps = src.count("/")
    return "{}/{}".format("/".join([".."] * seps), tgt)


if __name__ == "__main__":

    # Instantiate the parser
    parser = argparse.ArgumentParser(description='Generate go bindings and go plugins for proto files')

    # Optional argument
    parser.add_argument('--src', type=str,
                            help='Source directory to look for protos relative to current directory, default: staging')
    parser.add_argument('--dst', type=str,
                            help='Target directory generated bindings are placed relative to current directory, default: proto_go')

    # Switch
    parser.add_argument('--plugin', action='store_true',
                            help='build plugin libraries as well')
    parser.add_argument('--pluginAll', type=str,
                            help='build one plugin library which includes all proto symbols')
    args = parser.parse_args()

    if args.src:
        SRCDIR = args.src.rstrip('/')
    if args.dst:
        TGTDIR = args.dst.rstrip('/')

    print("Reading protos from: {}".format(SRCDIR))
    print("Target directory for generated proto bindings: {}".format(TGTDIR))
    if args.plugin:
        print("Target directory for plugins {}".format(TGTDIR))

    pluginSymList = []
    count = 0
    print("Soft links to protos and adding 'go generate' directive in gen.go...")
    l = createProtolist()
    for src,tgt,f in l:

        if not f.endswith(".proto"):
            continue

        count = count + 1

        srcfilename = os.path.join(src, f)
        tgtfilename = os.path.join(tgt, f)
        docsfile = os.path.join(tgt, "gen.go")

        package = extractPackageName(srcfilename)

        #
        # Make directory if it does not exist
        os.makedirs(tgt, exist_ok=True)

        #
        # Make symlink
        relativepath = extractRelativePath(tgtfilename, srcfilename)
        try:
            os.symlink(relativepath, tgtfilename)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            pass

        #
        # Write docs for go generate ./...
        # and add package if necessary
        doccontent = """
//go:generate protoc --go_out=plugins=grpc:{}/{} -I{}/{} {}
""".format(ABSPATHCWD, tgt, ABSPATHCWD, tgt, f)

        if not os.path.exists(docsfile):
            path = "{}/{}".format(REPOROOT, tgt)
            yangPath = ""
            doccontent = doccontent + """
{}
{}
            """.format(yangPath, package)

        # A messy way of creating it if it does not exist but reading content
        # looking for previous instances of go gen directives.
        with open(docsfile, "a+") as docfile:
            docfile.seek(0)
            if doccontent not in docfile.read():
                docfile.write(doccontent)

        if args.plugin:
            generatePluginGoCode(srcfilename, tgt, f)
        if args.pluginAll:
            generatePluginAllContent(srcfilename, tgt, f, pluginSymList)

    if args.pluginAll:
        print("Generating plugin.go file...")
        pluginContent = """
//go:generate go build -buildmode=plugin -o {} plugin.go

package main

import (
""".format(args.pluginAll)

        with open("plugin.go", "w") as p:
            p.write(pluginContent)
            for a, b, c, d in pluginSymList:
                import_line = """
      "./{}" """.format(a)
                p.write(import_line)

            p.write("""
)
""")
            for a, b, c, d in pluginSymList:
                l = """var KEYS_{} {}.{}
var CONTENT_{} {}.{}
""".format(b, b, c, b, b, d)
                p.write(l)


    print("Generating golang bindings for {} .proto files. This stage takes some time...".format(count))
    try:
        subprocess.check_call(["go", "generate", "./..."])
    except subprocess.CalledProcessError as e:
        try:
            print("Retrying the generation...\n")
            subprocess.check_call(["go", "generate", "./..."])
        except subprocess.CalledProcessError as e:
            print("'go generate' interprets .proto and builds go binding")
            print(" *** STAGE DID NOT RUN CLEAN. ERROR MESSAGE ABOVE. COMMON PROBLEMS BELOW ***")
            print(" GOROOT must be set to where golang is installed, minimum version go1.7 to run tests")
            print(" GOPATH must be workspace root")
            print(" Guidelines here: https://golang.org/doc/code.html")
            print(" protoc-gen-go must be in PATH (https://github.com/golang/protobuf)")
            print(" protoc must be in PATH")
            print(" go get -u github.com/golang/protobuf/{proto,protoc-gen-go}")
            print(e)

    print("Done.")
