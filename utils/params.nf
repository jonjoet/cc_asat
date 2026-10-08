// Pure normalization functions; failures are catchable by the transport harness.

def renderValue(value) {
    value instanceof CharSequence
        ? value.toString().replace('\\', '\\\\').replace("'", "\\'").replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
        : groovy.json.JsonOutput.toJson(value)
}

def normalizeCpu(value) {
    def text = value == null ? '' : value.toString().trim()
    if (!(value instanceof Boolean) && text ==~ /[0-9]+/) {
        def number = new BigInteger(text)
        if (number >= 1 && number <= 2147483647) return number.intValue()
    }
    throw new IllegalArgumentException("ERROR: --max_cpus must be an integer >= 1 (maximum 2147483647); received '${renderValue(value)}'.")
}

def normalizeMemory(value) {
    try {
        if (value instanceof nextflow.util.MemoryUnit) {
            if (value.toBytes() > 0) return value
        } else if (value instanceof CharSequence) {
            def text = value.toString().trim()
            def match = text =~ /(?i)^([0-9]+(?:\.[0-9]+)?)\s*([KMGTPE]?B?)$/
            if (match.matches() && match.group(2)) {
                def unit = match.group(2).toUpperCase(java.util.Locale.ROOT)
                def power = ['B':0, 'K':1, 'KB':1, 'M':2, 'MB':2, 'G':3, 'GB':3, 'T':4, 'TB':4, 'P':5, 'PB':5, 'E':6, 'EB':6][unit]
                if (power != null) {
                    def bytes = new BigDecimal(match.group(1)).multiply(new BigDecimal(1024).pow(power))
                    if (bytes >= 1 && bytes <= Long.MAX_VALUE) {
                        def parsed = new nextflow.util.MemoryUnit(text)
                        if (parsed.toBytes() > 0) return parsed
                    }
                }
            }
        }
    } catch (Exception ignored) { }
    throw new IllegalArgumentException("ERROR: --max_memory must be a positive memory quantity with units, e.g. '512 MB' or '8 GB'; received '${renderValue(value)}'.")
}

def normalizeTime(value) {
    try {
        if (value instanceof nextflow.util.Duration) {
            if (value.toMillis() > 0) return value
        } else if (value instanceof CharSequence) {
            def text = value.toString().trim()
            def scales = [ms:1, milli:1, millis:1, millisecond:1, milliseconds:1,
                s:1000, sec:1000, second:1000, seconds:1000,
                m:60000, min:60000, minute:60000, minutes:60000,
                h:3600000, hour:3600000, hours:3600000,
                d:86400000, day:86400000, days:86400000]
            def pieces = text =~ /(?i)([0-9]+(?:\.[0-9]+)?)\s*([a-z]+)/
            def total = new BigDecimal(0)
            def end = 0
            def valid = true
            pieces.each { piece ->
                def start = text.indexOf(piece[0], end)
                if (text.substring(end, start).trim()) valid = false
                def factor = scales[piece[2].toLowerCase(java.util.Locale.ROOT)]
                if (factor == null) valid = false
                else total = total.add(new BigDecimal(piece[1]).multiply(new BigDecimal(factor)))
                end = start + piece[0].length()
            }
            if (valid && end > 0 && !text.substring(end).trim() && total >= 1 && total <= Long.MAX_VALUE) {
                def parsed = new nextflow.util.Duration(text)
                if (parsed.toMillis() > 0) return parsed
            }
        }
    } catch (Exception ignored) { }
    throw new IllegalArgumentException("ERROR: --max_time must be a positive duration with units, e.g. '30min' or '12h'; received '${renderValue(value)}'.")
}

def normalizeBoolean(name, value, organism = null) {
    if (name == 'reorient_assembly' && value == null) return organism == 'bacterial'
    if (value instanceof Boolean) return value
    if (value instanceof CharSequence) {
        def text = value.toString().trim().toLowerCase(java.util.Locale.ROOT)
        if (text == 'true') return true
        if (text == 'false') return false
    }
    def grammar = name == 'reorient_assembly'
        ? 'a boolean (true or false) or YAML null for auto'
        : 'a boolean (true or false)'
    throw new IllegalArgumentException("ERROR: --${name} must be ${grammar}; received '${renderValue(value)}'.")
}

def normalizeOptions(values) {
    def result = [:]
    ['run_correct', 'fill_gaps_from_ref', 'skip_annotation_transfer', 'skip_merge',
     'liftoff_copies', 'fix_generic_names', 'fix_reference_gff', 'fix_vendor_gff',
     'merge_novel_only', 'reorient_assembly'].each { name ->
        result[name] = normalizeBoolean(name, values[name], values.organism_type)
    }
    return result.asImmutable()
}

def validateSelector(value) {
    if (!(value instanceof CharSequence) || !(value in ['full', 'annotation_transfer_only'])) {
        throw new IllegalArgumentException("ERROR: --workflow must be 'full' or 'annotation_transfer_only'; received '${renderValue(value)}'.")
    }
    return value
}

def preflight(values, legacy = false) {
    // Both entries deliberately use selector -> caps -> Booleans -> route inputs.
    validateSelector(values.workflow)
    def caps = [cpus: normalizeCpu(values.max_cpus),
                memory: normalizeMemory(values.max_memory), time: normalizeTime(values.max_time)]
    def options = normalizeOptions(values)
    def route = legacy ? 'annotation_transfer_only' : values.workflow
    if (route == 'full') {
        if (!values.assembly) error "ERROR: --assembly is required (pre-built de novo assembly FASTA)"
        if (!values.reference) error "ERROR: --reference is required (reference genome FASTA)"
        if (!(values.organism_type in ['fungal', 'bacterial'])) {
            error "ERROR: --organism_type is required and must be 'fungal' or 'bacterial'"
        }
        if (options.run_correct && !values.reads) error "ERROR: --run_correct requires --reads to be provided"
    } else {
        if (!values.assembly) error "ERROR: --assembly is required"
        if (!values.reference) error "ERROR: --reference is required"
        if (!values.reference_gff) error "ERROR: --reference_gff is required for annotation transfer"
    }
    log.info "Effective resource maxima: ${caps.cpus} CPUs, ${caps.memory.toBytes()} bytes, ${caps.time.toMillis()} ms"
    return options
}
