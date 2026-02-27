// BA-Agent Fantom Pod build definition
using build

class Build : BuildPod
{
  new make()
  {
    podName = "baAgent"
    summary = "Building Automation AI Agent - Haxall Extension"
    version = Version("0.1.0")
    depends = [
      "sys @{hx.dir}/lib/fan/",
      "util @{hx.dir}/lib/fan/",
      "web @{hx.dir}/lib/fan/",
      "haystack @{hx.dir}/lib/fan/",
      "axon @{hx.dir}/lib/fan/",
      "hx @{hx.dir}/lib/fan/",
      "hxPy @{hx.dir}/lib/fan/"
    ]
    srcDirs = [`fan/`]
    resDirs = [`axon/`, `assets/`]
  }
}
