// Test-only resource resolution and execution; production policy comes from nextflow.config.
include { RESOURCE_ORIGINAL as ALIASED } from '../parser_resources/parameters'

process PROBE_SINGLE {
    label 'process_single'
    output:
    path 'resolved.json'
    script:
    def record = groovy.json.JsonOutput.toJson([tier:'single', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()])
    """
    printf '%s\\n' '${record}' > resolved.json
    """
}

process RESOLVE_SINGLE {
    label 'process_single'
    output:
    path 'resolved.json'
    exec:
    def record = [tier:'single', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()]
    new File(task.workDir.toString(), 'resolved.json').text = groovy.json.JsonOutput.toJson(record)
}

process PROBE_LOW {
    label 'process_low'
    output:
    path 'resolved.json'
    script:
    def record = groovy.json.JsonOutput.toJson([tier:'low', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()])
    """
    printf '%s\\n' '${record}' > resolved.json
    """
}

process RESOLVE_LOW {
    label 'process_low'
    output:
    path 'resolved.json'
    exec:
    def record = [tier:'low', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()]
    new File(task.workDir.toString(), 'resolved.json').text = groovy.json.JsonOutput.toJson(record)
}

process PROBE_MEDIUM {
    label 'process_medium'
    output:
    path 'resolved.json'
    script:
    def record = groovy.json.JsonOutput.toJson([tier:'medium', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()])
    """
    printf '%s\\n' '${record}' > resolved.json
    """
}

process RESOLVE_MEDIUM {
    label 'process_medium'
    output:
    path 'resolved.json'
    exec:
    def record = [tier:'medium', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()]
    new File(task.workDir.toString(), 'resolved.json').text = groovy.json.JsonOutput.toJson(record)
}

process PROBE_HIGH {
    label 'process_high'
    output:
    path 'resolved.json'
    script:
    def record = groovy.json.JsonOutput.toJson([tier:'high', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()])
    """
    printf '%s\\n' '${record}' > resolved.json
    """
}

process RESOLVE_HIGH {
    label 'process_high'
    output:
    path 'resolved.json'
    exec:
    def record = [tier:'high', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()]
    new File(task.workDir.toString(), 'resolved.json').text = groovy.json.JsonOutput.toJson(record)
}

process PROBE_UNLABELLED {
    output:
    path 'resolved.json'
    script:
    def record = groovy.json.JsonOutput.toJson([tier:'unlabelled', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()])
    """
    printf '%s\\n' '${record}' > resolved.json
    """
}

process RESOLVE_UNLABELLED {
    output:
    path 'resolved.json'
    exec:
    def record = [tier:'unlabelled', attempt:task.attempt, task_id:task.id, name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()]
    new File(task.workDir.toString(), 'resolved.json').text = groovy.json.JsonOutput.toJson(record)
}

process PROBE_RETRY {
    label 'process_high'
    cpus { 1 * task.attempt }
    memory { 512.MB * task.attempt }
    time { 30.min * task.attempt }
    errorStrategy 'retry'
    maxRetries 1
    output:
    path 'resolved.json'
    script:
    def record = groovy.json.JsonOutput.toJson([tier:'retry', attempt:task.attempt, task_id:task.id,
        name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()])
    """
    printf '%s\\n' '${record}' > resolved.json
    test ${task.attempt} -eq 2
    """
}

workflow ALIAS_PATH {
    ALIASED()
}

workflow {
    if (params.probe_mode == 'alias') {
        ALIAS_PATH()
    } else if (params.probe_mode == 'retry') {
        PROBE_RETRY()
    } else if (params.probe_mode == 'resolution_only') {
        RESOLVE_SINGLE()
        RESOLVE_LOW()
        RESOLVE_MEDIUM()
        RESOLVE_HIGH()
        RESOLVE_UNLABELLED()
    } else {
        PROBE_SINGLE()
        PROBE_LOW()
        PROBE_MEDIUM()
        PROBE_HIGH()
        PROBE_UNLABELLED()
    }
}
