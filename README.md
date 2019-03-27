
# IOS XR Telemetry Proto Plugins

This repository contains "Go" plugins generated from IOS-XR protos at
[model-driven-telemetry](https://github.com/ios-xr/model-driven-telemetry). Go
plugins are like shared libraries that can be loaded dynamically into
Go executable. They will have to be built using the same version that the
executable is built with. Collectors can load these plugins
dynamically as needed to decode/unmarshal compact GPB
message.

There is a script available to generate Go bindings from the protos and
generate plugins from the bindings. Usage instructions for the
script as well as how plugins can be used with the collector are
specified below.

## Go bindings generation

prep_golang.py script can be used to generate the Go bindings. It is a
modified version of the script available at
[bigmuddy-network-telemetry-proto](https://github.com/cisco/bigmuddy-network-telemetry-proto). Along with generating Go
bindings, this script can generate plugins for each of these bindings
that can be used directly with the collectors at [telemetry-go-collector](https://github.com/ios-xr/telemetry-go-collector) to unmarshal gpb messages.

### Dependancies:
* go
* protoc
* protoc-gen-go
* python3

Plugins have to be built with the same Go version as the one used to build the
collectors, to be able to use them with the collectors. 

**Go version used to built plugins in this repo:**
```
 $ go version
go version go1.11.5 linux/amd64
 $ protoc --version
libprotoc 3.7.0
 $ 
```

## Script usage:  
```
./prep_golang.py --src <relative-path-to-protos> --dst <relative path to destination directory> --plugin
```
**Example:**  
Generate plugins for r65x protos,  
```
./prep_golang.py --src ../ios-xr/model-driven-telemetry/protos/65x --dst proto_go/65x --plugin
```
Generate only go bindings,  
```
./prep_golang.py --src ../ios-xr/model-driven-telemetry/protos/65x --dst proto_go/65x
```

**Note:**
This script is using absolute paths in "go generate" statements to
avoid protoc errors, if you are running the script to generate the bindgings or plugins
please delete proto_go directory first or you can directly use the
avialable bindings from proto_go directory.

```
 $ ./prep_golang.py --src ../model-driven-telemetry/protos/66x --dst proto_go/66x --plugin
Reading protos from: ../model-driven-telemetry/protos/66x
Target directory for generated proto bindings: proto_go/66x
Target directory for plugins proto_go/66x
Soft links to protos and adding 'go generate' directive in gen.go...
skiping plugin build for telemetry.proto
skiping plugin build for mdt_grpc_dialout.proto
skiping plugin build for mdt_grpc_dialin.proto
Generating golang bindings for 4117 .proto files. This stage takes some time...
Done.
 $ 
 $ ./prep_golang.py --src ../model-driven-telemetry/protos/65x --dst proto_go/65x --plugin
Reading protos from: ../model-driven-telemetry/protos/65x
Target directory for generated proto bindings: proto_go/65x
Target directory for plugins proto_go/65x
Soft links to protos and adding 'go generate' directive in gen.go...
skiping plugin build for telemetry.proto
skiping plugin build for mdt_grpc_dialout.proto
skiping plugin build for mdt_grpc_dialin.proto
Generating golang bindings for 4047 .proto files. This stage takes some time...
Done.
 $ 
```

## Plugins usage:
Collectors available at
https://github.com/ios-xr/telemetry-go-collector can use plugins
generated from this script to decode compact GPB encoded messages.

Plugins already available in this repo can be used with the collectors without need to rebuild them.

Use "go get" or "git clone" to get the repo:
```
git clone https://github.com/ios-xr/telemetry-proto-go-plugins.git
```
or
```
go get github.com/ios-xr/telemetry-proto-go-plugins
```

Usage example:
```
./bin/telemetry_dialin_collector -server <ip:port> -subscription <name> -encoding gpb -username <> -password <> -plugin_dir telemetry-proto-go-plugins/proto_go/66x
```
Collector will use encoding_path from telemetry message to construct the 
path to the plugin, add the path to plugin directory passed as input
to collector. If the plugin is found at that location, looks for the
symbols exported by the plugin and use them to unmarshal the keys and
the content of the messages.

The first example below shows collector failed to find the plugin, when
plugin directory is passed in, the message is decoded properly.
Examaple:
```
> ./telemetry-go-collector/bin/telemetry_dialin_collector -server 172.29.93.55:5701 -subscription mem -encoding gpb -username <> -password <>
mdtSubscribe: Dialin Reqid 369 subscription [mem]
plugin open failed plugin.Open("cisco_ios_xr_nto_misc_oper/memory_summary/nodes/node/summary/plugin/plugin.so"): realpath failed
{
  "NodeId": {
    "NodeIdStr": "ios"
  },
  "Subscription": {
    "SubscriptionIdStr": "mem"
  },
  "encoding_path": "Cisco-IOS-XR-nto-misc-oper:memory-summary/nodes/node/summary",
  "model_version": "2015-11-09",
  "collection_id": 3,
  "collection_start_time": 1553549994147,
  "msg_timestamp": 1553549994147,
  "data_gpb": {
    "row": [
      {
        "timestamp": 1553549994155,
        "keys": "CgowL1JQMC9DUFUw",
        "content": "kAOAIJgDgICAgBigA4DAuOAKqAOAgICAGLADgKDGlAq4A4CAgALAAwDIAwDQAwDYAwA="
      },
      {
        "timestamp": 1553549994159,
        "keys": "CggwLzAvQ1BVMA==",
        "content": "kAOAIJgDgICAgDCgA4DA+vAWqAOAgICAMLADgIDa9yS4A4CAgALAAwDIAwDQAwDYAwA="
      }
    ]
  },
  "collection_end_time": 1553549994160
}
^C $
 $
 $ ./telemetry-go-collector/bin/telemetry_dialin_collector -server 172.29.93.55:5701 -subscription mem -encoding gpb -username <> -password <> -plugin_dir telemetry-proto-go-plugins/proto_go/66x/
mdtSubscribe: Dialin Reqid 451 subscription [mem]
{
    "Telemetry": {
        "node_id_str": "ios",
        "subscription_id_str": "mem",
        "encoding_path": "Cisco-IOS-XR-nto-misc-oper:memory-summary/nodes/node/summary",
        "model_version": "2015-11-09",
        "collection_id": "4",
        "collection_start_time": "1553550022553",
        "msg_timestamp": "1553550022553",
        "data_gpbkv": [],
        "data_gpb": null,
        "collection_end_time": "1553550022566"
    },
    "Rows": [
        {
            "Timestamp": 1553550022561,
            "Keys": {
                "node_name": "0/RP0/CPU0"
            },
            "Content": {
                "page_size": 4096,
                "ram_memory": "6442450944",
                "free_physical_memory": "2886262784",
                "system_ram_memory": "6442450944",
                "free_application_memory": "2727075840",
                "image_memory": "4194304",
                "boot_ram_size": "0",
                "reserved_memory": "0",
                "io_memory": "0",
                "flash_system": "0"
            }
        },
        {
            "Timestamp": 1553550022565,
            "Keys": {
                "node_name": "0/0/CPU0"
            },
            "Content": {
                "page_size": 4096,
                "ram_memory": "12884901888",
                "free_physical_memory": "6141489152",
                "system_ram_memory": "12884901888",
                "free_application_memory": "9914859520",
                "image_memory": "4194304",
                "boot_ram_size": "0",
                "reserved_memory": "0",
                "io_memory": "0",
                "flash_system": "0"
            }
        }
    ]
}^C $
```
