"use strict";

const tabs = document.querySelectorAll(".tab-btn");
const panels = document.querySelectorAll(".tab-panel");

function setActiveTab(target) {
  tabs.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === target));
  panels.forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${target}`));
}

tabs.forEach((btn) => {
  btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
});

const fmt = (value, digits = 2) => {
  if (!Number.isFinite(value)) return "-";
  return value.toLocaleString("zh-CN", { maximumFractionDigits: digits });
};

const getNumber = (id) => {
  const val = Number(document.getElementById(id).value);
  return Number.isFinite(val) ? val : NaN;
};

const parseNumberList = (value) =>
  value
    .replace(/，/g, ",")
    .split(",")
    .map((v) => v.trim())
    .filter((v) => v.length)
    .map(Number)
    .filter((v) => Number.isFinite(v));

function setResult(el, text, isError = false) {
  el.textContent = text;
  el.classList.toggle("error", isError);
}

// =======================
// Tab 1: Cell counting
// =======================
const countResult = document.getElementById("count-result");

document.getElementById("count-calc").addEventListener("click", () => {
  const total = getNumber("count-total");
  const squares = getNumber("count-squares");
  const dilution = getNumber("count-dilution");
  const targetPerWell = getNumber("seed-target");
  const wellVol = getNumber("seed-well-volume");
  const wellsPerPlate = getNumber("seed-wells-per-plate");
  const plates = getNumber("seed-plates");
  const extra = getNumber("seed-extra");

  if ([total, squares, dilution, targetPerWell, wellVol, wellsPerPlate, plates, extra].some((v) => !Number.isFinite(v) || v <= 0)) {
    setResult(countResult, "请输入有效数字 (需 > 0)。", true);
    return;
  }

  const stockConc = (total / squares) * 10000 * dilution; // cells/mL
  const targetConc = targetPerWell / wellVol; // cells/mL
  const totalWells = wellsPerPlate * plates;
  const totalVol = totalWells * wellVol + extra; // mL
  const volStock = (targetConc * totalVol) / stockConc;
  const volMedia = totalVol - volStock;
  const totalCells = targetPerWell * totalWells;

  if (!Number.isFinite(volStock) || volStock <= 0) {
    setResult(countResult, "请检查输入数据是否合理。", true);
    return;
  }

  const warn = volMedia < 0 ? "\n注意：原液浓度偏低，无法配到目标密度。" : "";

  setResult(
    countResult,
    `【计算结果】\n` +
      `1. 原液细胞密度: ${fmt(stockConc / 10000, 2)} x 10^4 /mL\n` +
      `2. 铺板液目标密度: ${fmt(targetConc / 10000, 2)} x 10^4 /mL\n` +
      `3. 需要细胞总数: ${fmt(totalCells, 0)} 个\n` +
      `4. 需配制总体积: ${fmt(totalVol, 2)} mL (含余量)\n\n` +
      `操作方案:\n` +
      `  取细胞悬液: ${fmt(volStock, 3)} mL (${fmt(volStock * 1000, 1)} μL)\n` +
      `  + 培养基  : ${fmt(volMedia, 3)} mL` +
      warn
  );
});

// =======================
// Tab 2: Single drug
// =======================
const singleBody = document.getElementById("single-table-body");
const singleWarning = document.getElementById("single-warning");

document.getElementById("single-calc").addEventListener("click", () => {
  singleBody.innerHTML = "";
  singleWarning.textContent = "";

  const stock = getNumber("single-stock");
  const baseVol = getNumber("single-total-vol");
  const minStockVol = getNumber("single-min-stock");
  const targetsRaw = document.getElementById("single-targets").value;
  const mode = document.querySelector("input[name='single-mode']:checked").value;
  const multiplier = mode === "add" ? 2 : 1;

  if (![stock, baseVol, minStockVol].every((v) => Number.isFinite(v) && v > 0)) {
    singleWarning.textContent = "请输入有效的母液浓度、配制体积与最小取样体积。";
    return;
  }

  const targets = parseNumberList(targetsRaw);

  if (!targets.length) {
    singleWarning.textContent = "请输入至少一个目标浓度。";
    return;
  }

  if (targets.some((value) => value < 0)) {
    singleWarning.textContent = "目标浓度需为非负数。";
    return;
  }

  const uniqueTargets = [...new Set(targets)];
  const sortedTargets = uniqueTargets.sort((a, b) => b - a);
  const notes = [];
  const stockUM = stock * 1000;

  const isSorted = targets.every((value, index, list) => index === 0 || list[index - 1] >= value);
  const hasDuplicates = uniqueTargets.length !== targets.length;
  if (!isSorted || hasDuplicates) {
    notes.push(`已按浓度从高到低排序${hasDuplicates ? "，重复浓度已合并" : ""}。`);
  }

  if (mode === "add") {
    notes.push("方式B 已按 2X 计算配液浓度。");
  }

  const hasZero = sortedTargets.includes(0);
  const chainTargets = sortedTargets.filter((target) => target > 0);

  if (!chainTargets.length && hasZero) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${fmt(0, 2)}</td>
      <td>${fmt(0, 2)}</td>
      <td>培养基</td>
      <td>${fmt(0, 1)}</td>
      <td>${fmt(baseVol, 1)}</td>
    `;
    singleBody.appendChild(row);
    notes.push("所有终浓度为 0，仅需加培养基。");
    singleWarning.textContent = notes.join(" ");
    return;
  }

  const solutions = chainTargets.map((target) => target * multiplier);
  const maxSolution = Math.max(...solutions);

  if (maxSolution > stockUM) {
    singleWarning.textContent = "最高配液浓度高于母液浓度，无法配制。";
    return;
  }

  const calcData = chainTargets.map((target, index) => {
    const solution = target * multiplier;
    const isStock = index === 0;
    const sourceSolution = isStock ? stockUM : chainTargets[index - 1] * multiplier;
    const sourceName = isStock ? "母液" : `上一管 ${fmt(sourceSolution, 2)} μM`;
    return { target, solution, sourceSolution, sourceName, isStock };
  });

  const transferNeeds = new Array(calcData.length).fill(0);
  const results = new Array(calcData.length);
  let smallTransfers = false;
  let hasError = false;
  let stockAdjustNote = "";

  for (let index = calcData.length - 1; index >= 0; index -= 1) {
    const item = calcData[index];
    const baseTotalVol = baseVol + transferNeeds[index];
    let totalVol = baseTotalVol;
    let transferVol = (item.solution * totalVol) / item.sourceSolution;
    let note = "";

    if (item.isStock && transferVol > 0 && transferVol < minStockVol) {
      const factor = minStockVol / transferVol;
      totalVol = baseTotalVol * factor;
      transferVol = minStockVol;
      note = "已扩大体积以满足母液取样";
      stockAdjustNote = `已自动扩容：最高浓度管 ${fmt(baseTotalVol, 1)} μL → ${fmt(totalVol, 1)} μL (母液取样≥${fmt(minStockVol, 1)} μL)。`;
    }

    if (!item.isStock) {
      transferNeeds[index - 1] += transferVol;
      if (transferVol > 0 && transferVol < minStockVol) {
        smallTransfers = true;
      }
    }

    const mediaVol = totalVol - transferVol;
    const invalid = !Number.isFinite(mediaVol) || mediaVol < 0;

    if (invalid) {
      hasError = true;
    }

    results[index] = {
      ...item,
      transferVol,
      mediaVol,
      totalVol,
      note,
      invalid,
    };
  }

  results.forEach((res) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${fmt(res.target, 2)}</td>
      <td>${fmt(res.solution, 2)}</td>
      <td>${res.sourceName}</td>
      <td>${res.invalid ? "-" : fmt(res.transferVol, 3)}</td>
      <td>${res.invalid ? "母液不足" : fmt(res.mediaVol, 1)}</td>
    `;
    singleBody.appendChild(row);
  });

  if (hasZero) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${fmt(0, 2)}</td>
      <td>${fmt(0, 2)}</td>
      <td>培养基</td>
      <td>${fmt(0, 1)}</td>
      <td>${fmt(baseVol, 1)}</td>
    `;
    singleBody.appendChild(row);
  }

  if (calcData.length > 1) {
    notes.push("连续稀释已自动补偿传递体积，表中体积相加即每管实际配制总量。");
  }

  if (stockAdjustNote) {
    notes.push(stockAdjustNote);
  }

  if (smallTransfers) {
    notes.push("提示：部分梯度取样体积偏小，可适当增大每管总体积。");
  }

  if (hasError) {
    notes.push("部分浓度过高，无法用当前母液浓度配制。");
  }

  if (notes.length) {
    singleWarning.textContent = notes.join(" ");
  }
});

// =======================
// Tab 3: Double drug
// =======================
const doubleBody = document.getElementById("double-table-body");
const doubleWarning = document.getElementById("double-warning");

document.getElementById("double-calc").addEventListener("click", () => {
  doubleBody.innerHTML = "";
  doubleWarning.textContent = "";

  const stockA = getNumber("double-stock-a");
  const stockB = getNumber("double-stock-b");
  const totalVol = getNumber("double-total-vol");
  const targetsA = parseNumberList(document.getElementById("double-targets-a").value);
  const targetsB = parseNumberList(document.getElementById("double-targets-b").value);
  const mode = document.querySelector("input[name='double-mode']:checked").value;
  const multiplier = mode === "add" ? 2 : 1;

  if (![stockA, stockB, totalVol].every((v) => Number.isFinite(v) && v > 0)) {
    doubleWarning.textContent = "请输入有效的母液浓度与配制体积。";
    return;
  }

  if (!targetsA.length || !targetsB.length) {
    doubleWarning.textContent = "请输入药A与药B的终浓度序列 (μM)。";
    return;
  }

  const stockAUM = stockA * 1000;
  const stockBUM = stockB * 1000;

  const notes = [];
  let hasError = false;

  if (mode === "add") {
    notes.push("方式B 已按 2X 计算配液浓度。");
  }

  targetsA.forEach((targetA) => {
    targetsB.forEach((targetB) => {
      const solutionA = targetA * multiplier;
      const solutionB = targetB * multiplier;
      const volA = (solutionA * totalVol) / stockAUM;
      const volB = (solutionB * totalVol) / stockBUM;
      const volMedia = totalVol - volA - volB;

      let invalid = false;
      if (!Number.isFinite(volMedia) || volMedia < 0) {
        invalid = true;
        hasError = true;
      }

      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${fmt(targetA, 2)}</td>
        <td>${fmt(targetB, 2)}</td>
        <td>${invalid ? "-" : fmt(volA, 3)}</td>
        <td>${invalid ? "-" : fmt(volB, 3)}</td>
        <td>${invalid ? "母液不足" : fmt(volMedia, 1)}</td>
      `;
      doubleBody.appendChild(row);
    });
  });

  if (!doubleBody.children.length) {
    doubleWarning.textContent = "请输入药A与药B的终浓度序列 (μM)。";
    return;
  }

  if (hasError) {
    notes.push("部分组合过高，当前母液浓度无法配制。");
  }

  if (notes.length) {
    doubleWarning.textContent = notes.join(" ");
  }
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  });
}
