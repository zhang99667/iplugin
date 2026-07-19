#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";


const annotationSource = readFileSync(
  new URL("../../assets/annotation-mode/annotation.js", import.meta.url),
  "utf8",
);


/**
 * 从内联资产中提取指定函数，确保测试执行的就是最终注入报告的定位实现。
 * 这些函数不含模板字面量中的花括号，按函数体深度截取即可保持零依赖。
 */
function extractFunction(name) {
  const start = annotationSource.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `缺少函数 ${name}`);
  const openingBrace = annotationSource.indexOf("{", start);
  let depth = 0;
  for (let index = openingBrace; index < annotationSource.length; index += 1) {
    if (annotationSource[index] === "{") depth += 1;
    if (annotationSource[index] !== "}") continue;
    depth -= 1;
    if (depth === 0) return annotationSource.slice(start, index + 1);
  }
  throw new Error(`函数 ${name} 未正确闭合`);
}


const buildResolver = new Function(
  "function normalizeText(value) { return String(value || '').replace(/\\s+/g, ' ').trim(); }"
  + "function buildAnnotationCandidates() { throw new Error('测试必须显式传入候选节点'); }"
  + extractFunction("chooseUniqueAnnotationCandidate")
  + extractFunction("findAnnotationElementByText")
  + "; return { findAnnotationElementByText };",
);
const { findAnnotationElementByText } = buildResolver();


/** 构造最小 DOM 包含关系，验证父级大容器不会抢占更精确的正文节点。 */
function element(name, parent = null) {
  return {
    name,
    parent,
    contains(other) {
      let current = other;
      while (current) {
        if (current === this) return true;
        current = current.parent;
      }
      return false;
    },
  };
}


function candidate(target, text, sectionTitle = "章节") {
  return { element: target, text, sectionTitle };
}


const parent = element("parent");
const child = element("child", parent);
assert.equal(
  findAnnotationElementByText(
    { blockText: "唯一完整原文", selectedText: "完整原文", sectionTitle: "章节" },
    [candidate(parent, "前缀 唯一完整原文 后缀"), candidate(child, "唯一完整原文")],
  ),
  child,
  "完整块原文应迁移到唯一且最深的正文节点",
);

assert.equal(
  findAnnotationElementByText(
    { selectedText: "足够长的唯一选中文本", sectionTitle: "章节" },
    [candidate(parent, "父级 足够长的唯一选中文本 内容"), candidate(child, "足够长的唯一选中文本")],
  ),
  child,
  "选中文本同时命中父子节点时应选择更精确的子节点",
);

const left = element("left");
const right = element("right");
assert.equal(
  findAnnotationElementByText(
    { selectedText: "重复出现且足够长的选中文本", sectionTitle: "章节" },
    [candidate(left, "重复出现且足够长的选中文本"), candidate(right, "重复出现且足够长的选中文本")],
  ),
  null,
  "同章节存在多个候选时必须保持未解析，不能猜测位置",
);

assert.equal(
  findAnnotationElementByText(
    { selectedText: "重复出现且足够长的选中文本", sectionTitle: "目标章节" },
    [
      candidate(left, "重复出现且足够长的选中文本", "目标章节"),
      candidate(right, "重复出现且足够长的选中文本", "其他章节"),
    ],
  ),
  left,
  "章节信息可以把重复文本收敛到唯一候选",
);

console.log("PASS annotation location resolver");
