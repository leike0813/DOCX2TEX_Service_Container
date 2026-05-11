local LABEL_PATTERNS = {
  "^%s*图%s*%d+[%.%d]*[:：]",
  "^%s*表%s*%d+[%.%d]*[:：]",
  "^%s*式%s*%d+[%.%d]*[:：]",
  "^%s*Figure%s*%d+[%.%d]*[:：]",
  "^%s*Table%s*%d+[%.%d]*[:：]",
  "^%s*Fig%.%s*%d+[%.%d]*[:：]",
  "^%s*Eq%.%s*%d+[%.%d]*[:：]",
}

local function looks_like_numbered_caption_inlines(inlines)
  local s = pandoc.utils.stringify(inlines or {})
  for _, pat in ipairs(LABEL_PATTERNS) do
    if s:match(pat) then return true end
  end
  return false
end

local function replace_first_colon_in_inlines(inlines)
  for i = 1, #inlines do
    local il = inlines[i]
    if il.t == "Str" then
      if il.text == ":" or il.text == "：" then
        inlines[i] = pandoc.Space()
        return inlines
      else
        local replaced, n = il.text:gsub("[:：]", " ", 1)
        if n > 0 then
          inlines[i] = pandoc.Str(replaced)
          return inlines
        end
      end
    end
  end
  return inlines
end

local function fix_blocks_caption(blocks)
  if type(blocks) ~= "table" or #blocks == 0 then return blocks end
  local b = blocks[1]
  if b.t == "Plain" or b.t == "Para" then
    if looks_like_numbered_caption_inlines(b.c) then
      b.c = replace_first_colon_in_inlines(b.c)
      blocks[1] = b
      return blocks
    end
  end
  return blocks
end

function Caption(el)
  if el.long then
    el.long = fix_blocks_caption(el.long)
    return el
  end
  return nil
end

function Figure(el)
  if el.caption and el.caption.long then
    el.caption.long = fix_blocks_caption(el.caption.long)
    return el
  end
  return nil
end

function Table(el)
  if el.caption and el.caption.long then
    el.caption.long = fix_blocks_caption(el.caption.long)
    return el
  end
  if el.caption and el.caption[1] and el.caption[1].t == "Str" then
    if looks_like_numbered_caption_inlines(el.caption) then
      el.caption = replace_first_colon_in_inlines(el.caption)
      return el
    end
  end
  return nil
end

function Para(el)
  if looks_like_numbered_caption_inlines(el.c) then
    el.c = replace_first_colon_in_inlines(el.c)
    return el
  end
  return nil
end

function Plain(el)
  if looks_like_numbered_caption_inlines(el.c) then
    el.c = replace_first_colon_in_inlines(el.c)
    return el
  end
  return nil
end
