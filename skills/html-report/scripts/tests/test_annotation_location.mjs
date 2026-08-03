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
const buildFilterMatcher = new Function(
  extractFunction("isNoteKind") + extractFunction("matchesAnnotationFilter")
  + "; return { matchesAnnotationFilter };",
);
const { matchesAnnotationFilter } = buildFilterMatcher();
const runFilterControls = new Function(
  "annotations",
  "annotationFilter",
  "filterBar",
  extractFunction("isNoteKind")
  + extractFunction("matchesAnnotationFilter")
  + extractFunction("updateAnnotationFilterControls")
  + "; updateAnnotationFilterControls();",
);
const runLauncherUpdate = new Function(
  "annotations",
  "launcherLabel",
  "launcherCount",
  "launcher",
  extractFunction("updateLauncherMode") + "; updateLauncherMode();",
);
const buildRebind = new Function(
  extractFunction("buildReboundAnnotation") + "; return { buildReboundAnnotation };",
);
const { buildReboundAnnotation } = buildRebind();
const runCancelRebind = new Function(
  "window",
  "annotations",
  "let rebindAnnotationId = 'q-old';"
  + "let cachedSelectionTarget = { blockId: 'old-b001' };"
  + "let actionUpdates = 0;"
  + "function updateSelectionActionMode() { actionUpdates += 1; }"
  + "function hideSelectionPopover() {}"
  + extractFunction("cancelAnnotationRebind")
  + "; const cancelled = cancelAnnotationRebind();"
  + "; return { cancelled, rebindAnnotationId, cachedSelectionTarget, annotations, actionUpdates };",
);
const buildSelectionTarget = new Function(
  "window",
  "Node",
  "main",
  "normalizeText",
  "findQuestionTarget",
  "ensureBlockId",
  "nearestSectionId",
  "nearestSectionTitle",
  extractFunction("buildTargetFromSelection") + "; return { buildTargetFromSelection };",
);

assert.equal(isNoteKind("注释"), true, "新建内容应按注释类型展示");
assert.equal(isNoteKind("批注"), true, "旧评论包的批注类型必须继续兼容");
assert.equal(isNoteKind("提问"), false, "显式提问仍保留独立类型");
assert.equal(matchesAnnotationFilter({ kind: "提问" }, "question"), true, "提问筛选应保留提问");
assert.equal(matchesAnnotationFilter({ kind: "注释" }, "question"), false, "提问筛选应排除注释");
assert.equal(matchesAnnotationFilter({ kind: "批注" }, "note"), true, "注释筛选应兼容旧批注类型");
assert.equal(matchesAnnotationFilter({ kind: "提问" }, "all"), true, "全部筛选应保留所有类型");


/** 用最小控件桩执行数量同步，验证筛选切换不会污染批注数据。 */
function filterControlState(filter) {
  const buttons = ["all", "question", "note"].map(name => {
    const count = { textContent: "" };
    return {
      dataset: { qaFilter: name },
      classList: { active: false, toggle(_className, active) { this.active = active; } },
      attributes: {},
      setAttribute(name, value) { this.attributes[name] = value; },
      querySelector() { return count; },
      count,
    };
  });
  const filterBar = { querySelectorAll() { return buttons; } };
  runFilterControls(
    [{ kind: "提问" }, { kind: "注释" }, { kind: "批注" }],
    filter,
    filterBar,
  );
  return buttons;
}


const noteFilterButtons = filterControlState("note");
assert.equal(noteFilterButtons[0].count.textContent, "3", "全部筛选数量应包含旧批注类型");
assert.equal(noteFilterButtons[1].count.textContent, "1", "提问筛选数量应只统计提问");
assert.equal(noteFilterButtons[2].count.textContent, "2", "注释筛选数量应兼容注释和旧批注");
assert.equal(noteFilterButtons[2].classList.active, true, "当前筛选按钮应标记 active");
assert.equal(noteFilterButtons[2].attributes["aria-pressed"], "true", "当前筛选按钮应暴露 aria-pressed");


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


/** 重新关联只替换锚点字段，批注身份、正文和创建时间必须保持不变。 */
const originalAnnotation = {
  id: "q-old",
  kind: "提问",
  text: "原问题内容",
  createdAt: "2026-08-03T00:00:00.000Z",
  blockId: "old-b001",
  sectionId: "old-section",
  sectionTitle: "旧章节",
  selectedText: "旧选区",
  blockText: "旧正文",
  contextBefore: "旧前文",
  contextAfter: "旧后文",
  reportFileName: "report.html",
};
const rebound = buildReboundAnnotation(originalAnnotation, {
  blockId: "new-b002",
  sectionId: "new-section",
  sectionTitle: "新章节",
  selectedText: "新选区",
  blockText: "新正文",
  contextBefore: "新前文",
  contextAfter: "新后文",
});
assert.equal(rebound.id, originalAnnotation.id, "重新关联不得生成新批注 id");
assert.equal(rebound.text, originalAnnotation.text, "重新关联不得覆盖批注正文");
assert.equal(rebound.kind, originalAnnotation.kind, "重新关联不得改变批注类型");
assert.equal(rebound.createdAt, originalAnnotation.createdAt, "重新关联不得改变创建时间");
assert.equal(rebound.reportFileName, originalAnnotation.reportFileName, "重新关联不得丢失来源字段");
assert.deepEqual(
  {
    blockId: rebound.blockId,
    sectionId: rebound.sectionId,
    sectionTitle: rebound.sectionTitle,
    selectedText: rebound.selectedText,
    blockText: rebound.blockText,
    contextBefore: rebound.contextBefore,
    contextAfter: rebound.contextAfter,
  },
  {
    blockId: "new-b002",
    sectionId: "new-section",
    sectionTitle: "新章节",
    selectedText: "新选区",
    blockText: "新正文",
    contextBefore: "新前文",
    contextAfter: "新后文",
  },
  "重新关联应完整替换正文锚点字段",
);
assert.equal(originalAnnotation.blockId, "old-b001", "未确认新选区前旧批注对象不能被修改");

const cancelledState = runCancelRebind(
  { getSelection() { return { removeAllRanges() {} }; } },
  [originalAnnotation],
);
assert.equal(cancelledState.cancelled, true, "取消重新关联应返回已取消状态");
assert.equal(cancelledState.rebindAnnotationId, null, "取消后不应保留临时批注 id");
assert.equal(cancelledState.cachedSelectionTarget, null, "取消后不应保留旧选区缓存");
assert.deepEqual(cancelledState.annotations, [originalAnnotation], "取消重新关联不得改变批注数组");


/** 构造最小 Selection/Range 桩，验证手动重新关联只能接受 main 内正文选区。 */
function selectionState(insideMain) {
  const block = {
    innerText: "当前正文中的新选区",
    dataset: {},
  };
  const range = {
    commonAncestorContainer: { nodeType: 1 },
    getBoundingClientRect() { return { width: 80, top: 10, left: 10 }; },
  };
  const selection = {
    rangeCount: 1,
    isCollapsed: false,
    toString() { return "新选区"; },
    getRangeAt() { return range; },
  };
  const main = { contains() { return insideMain; } };
  const target = buildSelectionTarget(
    { getSelection() { return selection; } },
    { ELEMENT_NODE: 1 },
    main,
    value => String(value || "").replace(/\s+/g, " ").trim(),
    () => block,
    () => "section-b002",
    () => "section",
    () => "章节",
  ).buildTargetFromSelection();
  return target;
}

assert.equal(selectionState(false), null, "main 外选区必须被拒绝，不能重绑到批注 UI 或页面其他区域");
assert.equal(selectionState(true).selectedText, "新选区", "main 内合法选区应生成新的定位目标");


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
