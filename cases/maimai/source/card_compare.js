"use strict";
/**
 * Conservative card comparison; does not approve or send.
 * Input: JSON snapshots containing nonempty uid/name/text/contact_button.
 * ALL non-text fields are protected. Construct snapshots deliberately: capture
 * timestamps/hashes should not be supplied as business fields.
 * Only exact UI lines and verified city permutations in a bounded LF-only
 * list-card header may be ignored.
 */
const UI_LINES = new Set(["简历", "招聘动态", "近期有动向", "在线", "刚刚活跃", "今日活跃", "近1周活跃", "近1月活跃"]);
const ACTIVITY_LINES = new Set([...UI_LINES].filter(x => x !== "简历" && x !== "招聘动态" && x !== "近期有动向"));
const DATE_LINE = /^[0-9]{4}[.-][0-9]{2}(?:[.-][0-9]{2})?[ ]*-[ ]*(?:至今|[0-9]{4}[.-][0-9]{2}(?:[.-][0-9]{2})?)$/;
const PROTECTED_SECTIONS = new Set(["工作经历", "教育经历", "项目经历", "期望偏好", "【详情页补充，候选人自述】"]);
const HEADER_FIXED = new Set(["", "急求职", "正在看机会", "关注行情", "半年不看机会", "AI应用开发人才", "AI技术底座人才", "AI业务效能人才"]);
const EDUCATION_LINES = new Set(["博士", "硕士", "本科", "大专", "专科", "高中", "中专", "初中"]);
// Exact city tokens observed in the cross-snapshot fixtures.
const EXPECTATION_CITIES = new Set(["深圳", "广州", "上海", "郑州", "东莞", "杭州"]);
const EXPECTATION_LINE = /^期望：([^·]+)(·([1-9][0-9]{0,2})k-([1-9][0-9]{0,2})k·[A-Za-z0-9\u4e00-\u9fff+#().-]+(?:\/[A-Za-z0-9\u4e00-\u9fff+#().-]+)*)$/;
function cityOrder(line) {
  const match = EXPECTATION_LINE.exec(line);
  if (!match || match[0] !== line || Number(match[3]) > Number(match[4])) return null;
  const cities = match[1].split("/");
  if (cities.length < 2 || cities.length > 3 || new Set(cities).size !== cities.length) return null;
  if (cities.some(city => !EXPECTATION_CITIES.has(city))) return null;
  return "期望：" + cities.sort().join("/") + match[2];
}
function basicEnd(lines, start, end) {
  // No-expectation cards: protect the entire age?/experience/education?/location?
  // block up to its blank separator; never normalize or reorder location text.
  while (start < end && lines[start] === "") start++;
  let stop = start;
  while (stop < end && lines[stop] !== "") stop++;
  const core = lines.slice(start, stop);
  if (core.some(x => UI_LINES.has(x) || HEADER_FIXED.has(x))) return null;
  let index = 0;
  if (core.length && /^[0-9]+岁$/.test(core[0])) index++;
  if (index >= core.length || !/^[0-9]+年$/.test(core[index])) return null;
  index++;
  if (index < core.length && EDUCATION_LINES.has(core[index])) index++;
  if (core.length - index > 1) return null;
  if (index < core.length && (core[index].includes(":") || core[index].includes("："))) return null;
  return stop;
}
const object = x => x !== null && typeof x === "object" && !Array.isArray(x) && (Object.getPrototypeOf(x) === Object.prototype || Object.getPrototypeOf(x) === null);
function validJSON(x) {
  if (x === null || typeof x === "string" || typeof x === "boolean") return true;
  if (typeof x === "number") return Number.isFinite(x) && Math.abs(x) <= Number.MAX_SAFE_INTEGER;
  if (Array.isArray(x)) return x.every(validJSON);
  return object(x) && Object.values(x).every(validJSON);
}
function equal(a, b) {
  if (typeof a !== typeof b) return false;
  if (a === null || b === null || typeof a !== "object") return a === b;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) return a.length === b.length && a.every((x, i) => equal(x, b[i]));
  const keys = Object.keys(a);
  return keys.length === Object.keys(b).length && keys.every(k => Object.prototype.hasOwnProperty.call(b, k) && equal(a[k], b[k]));
}
function header(text, name, button, cityOrderOnly = false) {
  if (text.includes("\r")) return null;
  const lines = text.split("\n");
  if (lines[0] !== name) return null;
  let end = null;
  for (let index = 1; index < lines.length; index++) {
    const line = lines[index];
    if (PROTECTED_SECTIONS.has(line)) return null;
    // A list card may omit its employment start date. Keep exact standalone 至今
    // and every following line protected, including any UI-looking body text.
    if (line === "职业标签" || line === "职业标签：" || line === "至今" || DATE_LINE.test(line)) { end = index; break; }
  }
  if (end === null) return null;
  const buttons = [], expectations = [];
  for (let i = 1; i < end; i++) {
    if (lines[i] === button) buttons.push(i);
    if (lines[i].startsWith("期望：")) expectations.push(i);
  }
  if (buttons.length !== 1 || expectations.length > 1) return null;
  if (lines.slice(1, buttons[0]).some(x => !UI_LINES.has(x) && !HEADER_FIXED.has(x))) return null;
  let suffix;
  if (expectations.length) {
    if (buttons[0] >= expectations[0]) return null;
    suffix = expectations[0] + 1;
    if (lines.slice(buttons[0] + 1, expectations[0]).some(x => UI_LINES.has(x))) return null;
  } else {
    suffix = basicEnd(lines, buttons[0] + 1, end);
    if (suffix === null) return null;
  }
  if (lines.slice(suffix, end).some(x => !UI_LINES.has(x) && !HEADER_FIXED.has(x))) return null;
  const removed = lines.slice(1, end).filter(x => UI_LINES.has(x));
  if (removed.length !== new Set(removed).size || removed.filter(x => ACTIVITY_LINES.has(x)).length > 1) return null;
  if (cityOrderOnly) {
    if (expectations.length !== 1) return null;
    const index = expectations[0];
    const stop = basicEnd(lines, buttons[0] + 1, index);
    if (stop === null || lines.slice(stop, index).some(x => x !== "")) return null;
    const ordered = cityOrder(lines[index]);
    if (ordered === null) return null;
    lines[index] = ordered;
  }
  return [lines[0], ...lines.slice(1, end).filter(x => !UI_LINES.has(x)), ...lines.slice(end)].join("\n");
}
function compareCards(expected, actual) {
  const result = (equivalent, reason) => ({ equivalent, reason });
  for (const card of [expected, actual]) {
    if (!object(card) || !validJSON(card)) return result(false, "invalid_card");
    if (["uid", "name", "text", "contact_button"].some(k => typeof card[k] !== "string" || !card[k])) return result(false, "missing_required_field");
  }
  const before = Object.fromEntries(Object.entries(expected).filter(([k]) => k !== "text"));
  const after = Object.fromEntries(Object.entries(actual).filter(([k]) => k !== "text"));
  if (!equal(before, after)) return result(false, "non_text_field_changed");
  if (expected.text.split("\n")[0] !== expected.name || actual.text.split("\n")[0] !== actual.name) return result(false, "name_header_mismatch");
  if (expected.text === actual.text) return result(true, "exact");
  const left = header(expected.text, expected.name, expected.contact_button);
  const right = header(actual.text, actual.name, actual.contact_button);
  if (left === null || right === null) return result(false, "unrecognized_header");
  if (left !== right) {
    const orderedLeft = header(expected.text, expected.name, expected.contact_button, true);
    const orderedRight = header(actual.text, actual.name, actual.contact_button, true);
    if (orderedLeft !== null && orderedRight !== null && orderedLeft === orderedRight) return result(true, "header_city_order_only");
    return result(false, "protected_text_changed");
  }
  return result(true, "header_ui_only");
}
module.exports = { compareCards };
if (require.main === module) {
  // Use the exact same fixtures as Python, and compare full result objects.
  const { execFileSync } = require("node:child_process");
  const path = require("node:path");
  const pythonFile = path.join(__dirname, "card_compare.py");
  const cases = JSON.parse(execFileSync("python3", [pythonFile, "--emit-cases"], { encoding: "utf8" }));
  for (const test of cases) {
    const got = compareCards(test.expected, test.actual);
    if (got.equivalent !== test.want) throw Error(JSON.stringify({ name: test.name, got }));
  }
  const pythonResults = JSON.parse(execFileSync("python3", ["-c",
    "import json,sys;sys.path.insert(0,sys.argv[1]);import card_compare as c;print(json.dumps([c.compare_cards(x['expected'],x['actual']) for x in c.test_cases()]))",
    __dirname], { encoding: "utf8", env: {...process.env, PYTHONHASHSEED: "0"} }));
  // Python set iteration order is process-dependent; get one stable fixture set.
  const stableCases = JSON.parse(execFileSync("python3", [pythonFile, "--emit-cases"], { encoding: "utf8", env: {...process.env, PYTHONHASHSEED: "0"} }));
  stableCases.forEach((test, i) => {
    if (!equal(compareCards(test.expected, test.actual), pythonResults[i])) throw Error("Python/JS mismatch: " + test.name);
  });
  process.stdout.write(JSON.stringify({passed: cases.length, failed: 0, parity: stableCases.length}) + "\n");
}
