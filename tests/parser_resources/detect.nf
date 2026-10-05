workflow {
    println groovy.json.JsonOutput.toJson([raw_cpus:Runtime.runtime.availableProcessors(), raw_max_memory:Runtime.runtime.maxMemory()])
}
