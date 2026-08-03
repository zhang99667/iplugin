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
const buildKindMatcher = new Function(extractFunction("isNoteKind") + "; return { isNoteKind };");
const { isNoteKind } = buildKindMatcher();
const runLauncherUpdate = new Function(
  "annotations",
  "launcherLabel",
  "launcherCount",
  "launcher",
  extractFunction("updateLauncherMode") + "; updateLauncherMode();",
);

assert.equal(isNoteKind("注释"), true, "新建内容应按注释类型展示");
assert.equal(isNoteKind("批注"), true, "旧评论包的批注类型必须继续兼容");
assert.equal(isNoteKind("提问"), false, "显式提问仍保留独立类型");


/** 直接执行正式入口状态函数，验证数量只改变徽标，不改变按钮职责。 */
function launcherState(count) {
  const launcherLabel = { textContent: "" };
  const launcherCount = { textContent: "", hidden: false };
  const attributes = {};
  const launcher = {
    setAttribute(name, value) {
      attributes[name] = value;
    },
  };
  runLauncherUpdate(Array.from({ length: count }), launcherLabel, launcherCount, launcher);
  return { launcherLabel, launcherCount, attributes };
}


const emptyLauncher = launcherState(0);
assert.equal(emptyLauncher.launcherLabel.textContent, "批注", "零条时入口仍应显示批注");
assert.equal(emptyLauncher.launcherCount.hidden, true, "零条时应隐藏数量徽标");
assert.equal(emptyLauncher.attributes["aria-label"], "打开报告批注", "零条入口应说明打开批注工作区");

const populatedLauncher = launcherState(3);
assert.equal(populatedLauncher.launcherLabel.textContent, "批注", "有批注时入口文案也不能改变职责");
assert.equal(populatedLauncher.launcherCount.textContent, "3", "数量徽标应反映当前批注数");
assert.equal(populatedLauncher.launcherCount.hidden, false, "有批注时应显示数量徽标");
assert.equal(populatedLauncher.attributes["aria-label"], "打开报告批注，当前 3 条", "有批注时应补充可访问数量");


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

console.log("PASS annotation runtime helpers");
