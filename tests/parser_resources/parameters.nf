// Each row crosses actual engine transport and calls the production function independently.
include { normalizeCpu; normalizeMemory; normalizeTime; normalizeBoolean; renderValue } from '../../utils/params'

process RESOURCE_ORIGINAL {
    label 'process_high'
    output:
    path 'resolved.json'
    script:
    def record = groovy.json.JsonOutput.toJson([tier:'alias', attempt:task.attempt, task_id:task.id,
        name:task.name, cpus:task.cpus, memory_bytes:task.memory.toBytes(), time_ms:task.time.toMillis()])
    """
    printf '%s\\n' '${record}' > resolved.json
    """
}

def unwrappedCause(failure) {
    return failure instanceof java.lang.reflect.InvocationTargetException && failure.cause != null
        ? unwrappedCause(failure.cause) : failure
}

workflow {
    def cases = new groovy.json.JsonSlurper().parseText(file(params.batch_manifest).text)
    def records = []
    cases.each { row ->
        def value = row.omitted ? row.default_value : params[row.key]
        def record = [id:row.id, parameter:row.parameter, input_type:value == null ? 'null' : value.getClass().name,
                      received:renderValue(value)]
        try {
            if (row.native_object) {
                value = row.parameter == 'max_memory'
                    ? new nextflow.util.MemoryUnit(value.toString())
                    : new nextflow.util.Duration(value.toString())
            }
            def normalized = null
            if (row.parameter == 'max_cpus') normalized = normalizeCpu(value)
            else if (row.parameter == 'max_memory') normalized = normalizeMemory(value).toBytes()
            else if (row.parameter == 'max_time') normalized = normalizeTime(value).toMillis()
            else normalized = normalizeBoolean(row.parameter, value, row.organism)
            record.value = normalized
            record.type = normalized.getClass().name
            if (row.observe_native) {
                def nativeValue = row.parameter == 'max_memory'
                    ? new nextflow.util.MemoryUnit(value.toString())
                    : new nextflow.util.Duration(value.toString())
                record.native_value = row.parameter == 'max_memory' ? nativeValue.toBytes() : nativeValue.toMillis()
                if (row.native_object) {
                    record.native_identity = row.parameter == 'max_memory'
                        ? normalizeMemory(value).is(value) : normalizeTime(value).is(value)
                    // Native objects can stringify at lower precision; observe the object itself.
                    record.native_value = row.parameter == 'max_memory' ? value.toBytes() : value.toMillis()
                }
            }
        } catch (Exception failure) {
            def cause = unwrappedCause(failure)
            record.error = cause.message
        }
        records.add(record)
    }
    file(params.batch_output).text = groovy.json.JsonOutput.toJson(records)
}
