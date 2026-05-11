local function strip_control_chars(text)
  if not text then
    return text
  end
  return text:gsub("[%z\1-\8\11-\31]", "")
end

local function find_matching_brace(text, start_pos)
  local depth = 0
  local i = start_pos
  while i <= #text do
    local ch = text:sub(i, i)
    if ch == "\\" then
      i = i + 1
    elseif ch == "{" then
      depth = depth + 1
    elseif ch == "}" then
      depth = depth - 1
      if depth == 0 then
        return i
      end
    end
    i = i + 1
  end
  return nil
end

local function needs_mathit(content)
  if not content then
    return false
  end
  local stripped = content:gsub("%s+", "")
  if stripped:match("^\\mathit") then
    return false
  end
  if stripped:match("^\\?[A-Za-z]$") then
    return true
  end
  if stripped:match("^\\?[%a][_%w%d]*$") then
    return true
  end
  return false
end

local function wrap_boldsymbol_arguments(text)
  local i = 1
  local pieces = {}
  while i <= #text do
    local j = text:find("\\boldsymbol", i, true)
    if not j then
      table.insert(pieces, text:sub(i))
      break
    end
    table.insert(pieces, text:sub(i, j - 1))
    local k = j + #"\\boldsymbol"
    while k <= #text and text:sub(k, k):match("%s") do
      k = k + 1
    end
    if text:sub(k, k) ~= "{" then
      table.insert(pieces, "\\boldsymbol")
      i = k
    else
      local closing = find_matching_brace(text, k)
      if not closing then
        table.insert(pieces, text:sub(j))
        break
      end
      local content = text:sub(k + 1, closing - 1)
      if needs_mathit(content) then
        table.insert(pieces, "\\boldsymbol{\\mathit{" .. content .. "}}")
      else
        table.insert(pieces, text:sub(j, closing))
      end
      i = closing + 1
    end
  end
  return table.concat(pieces)
end

local function clean_math(el)
  local text = el.text or ""
  local cleaned = strip_control_chars(text)
  cleaned = wrap_boldsymbol_arguments(cleaned)
  if cleaned ~= text then
    return pandoc.Math(el.mathtype, cleaned)
  end
end

function Math(el)
  return clean_math(el)
end

function DisplayMath(el)
  return clean_math(el)
end

function Str(el)
  local cleaned = strip_control_chars(el.text or "")
  if cleaned == "" then
    return nil
  end
  if cleaned ~= el.text then
    return pandoc.Str(cleaned)
  end
end
