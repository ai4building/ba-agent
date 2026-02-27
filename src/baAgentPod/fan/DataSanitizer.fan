// BA-Agent Data Sanitizer — strips sensitive fields from Haystack data
using haystack

**
** DataSanitizer recursively removes sensitive fields (passwords, tokens, API keys)
** from Dict and Grid data before returning results to clients.
**
** All responses flowing through BaAgentWeb are sanitized to prevent
** accidental leakage of credentials or secrets stored in point tags.
**
const class DataSanitizer
{
  ** Sensitive key patterns — matched case-insensitively against Dict keys.
  private static const Str[] sensitiveKeys := [
    "password", "secret", "apiKey", "token",
    "credential", "privateKey", "ssn",
    "apikey", "api_key", "private_key"
  ]

  ** Recursively sanitize a Dict, removing any keys that match sensitiveKeys.
  static Dict sanitize(Dict dict)
  {
    tags := Str:Obj?[:]
    dict.each |v, k|
    {
      if (isSensitive(k)) return  // skip sensitive keys

      // Recurse into nested Dict values
      if (v is Dict)
        tags[k] = sanitize(v)
      // Recurse into List values
      else if (v is List)
        tags[k] = sanitizeList(v)
      else
        tags[k] = v
    }
    return Etc.makeDict(tags)
  }

  ** Sanitize every row in a Grid.
  static Grid sanitizeGrid(Grid grid)
  {
    rows := Dict[,]
    grid.each |row| { rows.add(sanitize(row)) }

    // Rebuild grid with sanitized rows
    if (rows.isEmpty)
      return Grid.makeListGrid(grid.meta, Str[,], Obj?[,], Obj?[][,])

    return Etc.makeDictsGrid(grid.meta, rows)
  }

  ** Check whether a key name matches any sensitive pattern (case-insensitive).
  static Bool isSensitive(Str key)
  {
    lower := key.lower
    return sensitiveKeys.any |s| { lower.contains(s.lower) }
  }

  ** Sanitize list elements — recurse into Dict items.
  private static List sanitizeList(List list)
  {
    return list.map |item|
    {
      if (item is Dict) return sanitize(item)
      if (item is List) return sanitizeList(item)
      return item
    }
  }
}
