import React, { useState, useMemo } from "react";
import { AccessibleModal } from "./AccessibleModal";
import { ServedConstantsView } from "./ServedConstantsView";
import {
  Database,
  Search,
  ArrowUpDown,
  Flame,
  Wrench,
  AlertTriangle,
  Info,
  SlidersHorizontal,
  CheckSquare,
  Square,
  Layers,
  Copy,
  Check,
  Download,
  Scale,
  Sparkles,
  BarChart2,
  X,
  Grid,
  LayoutGrid,
} from "lucide-react";
import { MATERIALS_DATABASE } from "../data/materialsDatabase";
import { MaterialSpec } from "../types";
import { MaterialsPropertyHeatmapD3 } from "./MaterialsPropertyHeatmapD3";
import { SendToModuleButton } from "./SendToModuleButton";
import { AlloyBuilder } from "./AlloyBuilder";
import { createPipelinePayloadFromMaterialSpec, setActivePipelineMaterial } from "../utils/materialDataPipeline";
import { Zap, Atom, Gauge } from "lucide-react";

interface MaterialsDatabaseViewProps {
  onNavigate?: (tabId: string) => void;
}

export const MaterialsDatabaseView: React.FC<MaterialsDatabaseViewProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<"split" | "heatmap" | "catalog">("split");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [selectedMaterial, setSelectedMaterial] = useState<MaterialSpec>(
    MATERIALS_DATABASE[0]
  );
  const [sortBy, setSortBy] = useState<"name" | "yield" | "tensile" | "modulus" | "density" | "specific_strength">("yield");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");
  
  // Property range filters
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [minYield, setMinYield] = useState<number>(0);
  const [maxYield, setMaxYield] = useState<number>(3500);
  const [minModulus, setMinModulus] = useState<number>(40);
  const [maxModulus, setMaxModulus] = useState<number>(650);
  const [minDensity, setMinDensity] = useState<number>(1.5);
  const [maxDensity, setMaxDensity] = useState<number>(17.0);

  // Comparison drawer state
  const [compareList, setCompareList] = useState<MaterialSpec[]>([MATERIALS_DATABASE[0], MATERIALS_DATABASE[5]]);
  const [isCompareOpen, setIsCompareOpen] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const categories = [
    "All",
    "Carbon Steel",
    "Alloy Steel",
    "Tool Steel",
    "Stainless Steel",
    "Aluminum Alloy",
    "Copper Alloy",
    "Titanium Alloy",
    "Nickel Superalloy",
    "Magnesium Alloy",
    "Refractory & Specialty",
    "Ceramic & Carbide",
  ];

  const filteredMaterials = useMemo(() => {
    return MATERIALS_DATABASE.filter((mat) => {
      const q = searchQuery.toLowerCase().trim();
      const matchSearch =
        !q ||
        mat.name.toLowerCase().includes(q) ||
        mat.standard.toLowerCase().includes(q) ||
        mat.category.toLowerCase().includes(q) ||
        mat.microstructure.toLowerCase().includes(q) ||
        mat.applications.some((app) => app.toLowerCase().includes(q)) ||
        Object.keys(mat.composition).some((elem) => elem.toLowerCase() === q || elem.toLowerCase().includes(q));

      const matchCategory =
        selectedCategory === "All" || mat.category === selectedCategory;

      const matchYield = mat.yieldStrength >= minYield && mat.yieldStrength <= maxYield;
      const matchModulus = mat.youngsModulus >= minModulus && mat.youngsModulus <= maxModulus;
      const matchDensity = mat.density >= minDensity && mat.density <= maxDensity;

      return matchSearch && matchCategory && matchYield && matchModulus && matchDensity;
    }).sort((a, b) => {
      let diff = 0;
      if (sortBy === "yield") diff = b.yieldStrength - a.yieldStrength;
      else if (sortBy === "tensile") diff = b.tensileStrength - a.tensileStrength;
      else if (sortBy === "modulus") diff = b.youngsModulus - a.youngsModulus;
      else if (sortBy === "density") diff = b.density - a.density;
      else if (sortBy === "specific_strength") {
        const specA = a.yieldStrength / a.density;
        const specB = b.yieldStrength / b.density;
        diff = specB - specA;
      } else {
        diff = a.name.localeCompare(b.name);
      }
      return sortOrder === "desc" ? diff : -diff;
    });
  }, [searchQuery, selectedCategory, sortBy, sortOrder, minYield, maxYield, minModulus, maxModulus, minDensity, maxDensity]);

  const toggleCompare = (mat: MaterialSpec) => {
    if (compareList.some((m) => m.id === mat.id)) {
      setCompareList(compareList.filter((m) => m.id !== mat.id));
    } else {
      if (compareList.length < 4) {
        setCompareList([...compareList, mat]);
      }
    }
  };

  const handleCopySpec = () => {
    const jsonStr = JSON.stringify(selectedMaterial, null, 2);
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportAllJSON = () => {
    const blob = new Blob([JSON.stringify(MATERIALS_DATABASE, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "metallurgical_materials_database.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div id="materials-database-view" className="space-y-5">
      <ServedConstantsView />
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-[#090e18] border border-[#162032]">
        <div>
          <div className="flex items-center gap-2 text-sky-400 font-mono text-[10px] font-semibold uppercase tracking-widest">
            <Database className="w-3.5 h-3.5 text-sky-400" />
            Engineering Materials Specification & Property Library
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">Searchable Metallurgical Materials Database</h2>
          <p className="text-xs text-slate-400 max-w-3xl mt-0.5">
            Chemical compositions, tensile & yield strength, Young&apos;s modulus, density, microstructures, heat treatments, and applications for steels, aluminum, titanium, copper, nickel superalloys, magnesium & refractories.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 bg-[#050810] p-1 rounded-xl border border-[#162032]">
            <button
              type="button"
              onClick={() => setActiveTab("split")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition ${
                activeTab === "split"
                  ? "bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-[0_0_8px_rgba(56,189,248,0.2)]"
                  : "text-slate-400 hover:text-white border border-transparent"
              }`}
              title="Split View: D3 Heatmap & Detailed Dossier"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Split View</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("heatmap")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition ${
                activeTab === "heatmap"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.2)]"
                  : "text-slate-400 hover:text-white border border-transparent"
              }`}
              title="Full Screen D3 Heatmap & Correlation Matrix"
            >
              <Grid className="w-3.5 h-3.5" />
              <span>D3 Heatmap</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("catalog")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition ${
                activeTab === "catalog"
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-[0_0_8px_rgba(99,102,241,0.2)]"
                  : "text-slate-400 hover:text-white border border-transparent"
              }`}
              title="Catalog List & Detailed Spec Sheet"
            >
              <Database className="w-3.5 h-3.5" />
              <span>Catalog Only</span>
            </button>
          </div>

          {compareList.length > 0 && (
            <button
              onClick={() => setIsCompareOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 text-xs font-mono font-bold hover:bg-indigo-500/30 transition shadow-[0_0_12px_rgba(99,102,241,0.2)]"
            >
              <Scale className="w-3.5 h-3.5" />
              <span>Compare ({compareList.length}/4)</span>
            </button>
          )}
          <button
            onClick={handleExportAllJSON}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0c1322] text-slate-300 border border-[#162032] text-xs font-mono hover:text-white hover:border-[#243450] transition"
          >
            <Download className="w-3.5 h-3.5 text-sky-400" />
            <span>Export Database</span>
          </button>
        </div>
      </div>

      {/* Search, Filter Bar & Quick Stats */}
      <div className="space-y-3">
        <div className="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center justify-between">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
            <input aria-label="Filter materials"
              type="text"
              placeholder="Search alloy name, UNS, ASTM, composition (e.g., Ti, Ni, Cu), application..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-2 bg-[#090e18] border border-[#162032] rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-400 font-sans"
            />
          </div>

          {/* Filter toggle & Sort Selector */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs rounded-lg border font-mono transition ${
                showFilters || minYield > 0 || minModulus > 40 || minDensity > 1.5
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                  : "bg-[#090e18] text-slate-400 border-[#162032] hover:text-white"
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Property Sliders</span>
              {(minYield > 0 || minModulus > 40 || minDensity > 1.5) && (
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              )}
            </button>

            {/* Sort Selector */}
            <div className="flex items-center gap-1 bg-[#090e18] border border-[#162032] rounded-lg p-0.5 text-xs text-slate-400">
              <span className="pl-2 font-mono text-[10px] text-slate-500">Sort:</span>
              <select aria-label="Sort"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-transparent px-2 py-1.5 text-xs text-slate-200 focus:outline-none font-mono"
              >
                <option value="yield" className="bg-[#090e18]">Yield Strength (σy)</option>
                <option value="tensile" className="bg-[#090e18]">Tensile Strength (UTS)</option>
                <option value="specific_strength" className="bg-[#090e18]">Specific Strength (σy/ρ)</option>
                <option value="modulus" className="bg-[#090e18]">Young&apos;s Modulus (E)</option>
                <option value="density" className="bg-[#090e18]">Density (ρ)</option>
                <option value="name" className="bg-[#090e18]">Alloy Name (A-Z)</option>
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === "desc" ? "asc" : "desc")}
                className="p-1.5 hover:text-white transition"
                title="Toggle Sort Order"
              >
                <ArrowUpDown className="w-3.5 h-3.5 text-sky-400" />
              </button>
            </div>
          </div>
        </div>

        {/* Categories Pills */}
        <div className="flex flex-wrap gap-1.5 p-1 bg-[#090e18] rounded-xl border border-[#162032] overflow-x-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 text-xs rounded-lg transition whitespace-nowrap font-mono ${
                selectedCategory === cat
                  ? "bg-sky-500/20 border border-sky-400/60 text-sky-300 font-bold shadow-[0_0_10px_rgba(56,189,248,0.2)]"
                  : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Collapsible Range Sliders */}
        {showFilters && (
          <div className="p-4 bg-[#090e18] rounded-xl border border-[#162032] grid grid-cols-1 md:grid-cols-3 gap-4 animate-in fade-in duration-200">
            {/* Yield Strength Slider */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">Yield Strength (σy):</span>
                <span className="text-emerald-400 font-bold">{minYield} – {maxYield} MPa</span>
              </div>
              <div className="flex items-center gap-2">
                <input aria-label="Minimum Yield Strength (σy) (MPa)"
                  type="range"
                  min="0"
                  max="3500"
                  step="50"
                  value={minYield}
                  onChange={(e) => setMinYield(Number(e.target.value))}
                  className="w-full accent-emerald-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
              </div>
            </div>

            {/* Young's Modulus Slider */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">Young&apos;s Modulus (E):</span>
                <span className="text-cyan-400 font-bold">{minModulus} – {maxModulus} GPa</span>
              </div>
              <div className="flex items-center gap-2">
                <input aria-label="Minimum Young's Modulus (E) (GPa)"
                  type="range"
                  min="40"
                  max="650"
                  step="10"
                  value={minModulus}
                  onChange={(e) => setMinModulus(Number(e.target.value))}
                  className="w-full accent-cyan-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
              </div>
            </div>

            {/* Density Slider */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">Density (ρ):</span>
                <span className="text-amber-400 font-bold">{minDensity.toFixed(1)} – {maxDensity.toFixed(1)} g/cm³</span>
              </div>
              <div className="flex items-center gap-2">
                <input aria-label="Maximum Density (ρ) (g/cm³)"
                  type="range"
                  min="1.5"
                  max="17.0"
                  step="0.2"
                  value={maxDensity}
                  onChange={(e) => setMaxDensity(Number(e.target.value))}
                  className="w-full accent-amber-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
              </div>
            </div>

            <div className="md:col-span-3 flex justify-end">
              <button
                onClick={() => {
                  setMinYield(0);
                  setMaxYield(3500);
                  setMinModulus(40);
                  setMaxModulus(650);
                  setMinDensity(1.5);
                  setMaxDensity(17.0);
                }}
                className="text-[11px] font-mono text-slate-400 hover:text-white underline"
              >
                Reset Range Filters
              </button>
            </div>
          </div>
        )}
      </div>

      {/* D3.js Composition & Property Heatmap (Rendered in 'split' or 'heatmap' mode) */}
      {(activeTab === "split" || activeTab === "heatmap") && (
        <div className="animate-in fade-in duration-200">
          <MaterialsPropertyHeatmapD3
            materials={filteredMaterials}
            selectedMaterial={selectedMaterial}
            onSelectMaterial={(mat) => setSelectedMaterial(mat)}
            categories={categories}
            activeCategory={selectedCategory}
            onSelectCategory={(cat) => setSelectedCategory(cat)}
          />
        </div>
      )}

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
        <span>Showing {filteredMaterials.length} of {MATERIALS_DATABASE.length} materials</span>
        <span>Click an alloy from the list or heatmap to inspect full metallurgical dossier</span>
      </div>

      {/* Main Grid: List (Left) + Detail Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Materials Table / Cards */}
        <div className="lg:col-span-5 space-y-2.5 max-h-[850px] overflow-y-auto pr-1">
          {filteredMaterials.map((mat) => {
            const isSelected = selectedMaterial.id === mat.id;
            const isComparing = compareList.some((m) => m.id === mat.id);
            const specificStrength = (mat.yieldStrength / mat.density).toFixed(1);

            return (
              <div
                key={mat.id}
                onClick={() => setSelectedMaterial(mat)}
                className={`p-3.5 rounded-xl border cursor-pointer transition relative group ${
                  isSelected
                    ? "bg-sky-500/15 border-sky-400/60 text-sky-200 shadow-[0_0_15px_rgba(56,189,248,0.15)]"
                    : "bg-[#090e18] border-[#162032] hover:border-[#243450] hover:bg-white/[0.02]"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-bold text-sm text-white font-mono">{mat.name}</span>
                    </div>
                    <div className="text-[10px] font-mono text-sky-400/90 mt-0.5">{mat.standard}</div>
                  </div>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleCompare(mat);
                    }}
                    className={`p-1 rounded text-xs transition ${
                      isComparing
                        ? "text-indigo-400 bg-indigo-500/20 border border-indigo-500/40"
                        : "text-slate-500 hover:text-slate-300 opacity-0 group-hover:opacity-100"
                    }`}
                    title={isComparing ? "Remove from comparison" : "Add to comparison"}
                  >
                    {isComparing ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                  </button>
                </div>

                <div className="text-xs text-slate-400 mt-1.5 line-clamp-2">{mat.microstructure}</div>

                <div className="grid grid-cols-4 gap-1.5 mt-2.5 pt-2 border-t border-[#162032] text-[10px] font-mono">
                  <div>
                    <span className="text-slate-500 block text-[9px]">Yield (σy)</span>
                    <span className="font-bold text-emerald-400">{mat.yieldStrength} MPa</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[9px]">Modulus (E)</span>
                    <span className="font-bold text-cyan-400">{mat.youngsModulus} GPa</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[9px]">Density (ρ)</span>
                    <span className="font-bold text-amber-400">{mat.density} g/cm³</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[9px]">σy/ρ</span>
                    <span className="font-bold text-indigo-400">{specificStrength}</span>
                  </div>
                </div>
              </div>
            );
          })}

          {filteredMaterials.length === 0 && (
            <div className="p-8 text-center bg-[#090e18] rounded-xl border border-[#162032] text-slate-400 space-y-2">
              <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto" />
              <div className="font-mono text-sm text-white">No materials matched your filter</div>
              <p className="text-xs">Try broadening your search query or adjusting the property range sliders.</p>
            </div>
          )}
        </div>

        {/* Right: Detailed Material Spec Sheet */}
        <div className="lg:col-span-7 bg-[#090e18] rounded-xl border border-[#162032] p-5 space-y-5">
          {/* Header Info */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#162032]">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-md bg-sky-500/20 text-sky-300 text-xs font-mono font-bold border border-sky-400/30">
                  {selectedMaterial.category}
                </span>
                <span className="text-xs font-mono text-slate-400">{selectedMaterial.standard}</span>
              </div>
              <h3 className="text-xl font-bold text-white mt-1.5 font-mono">{selectedMaterial.name}</h3>
              <p className="text-xs text-slate-400 mt-0.5">Melting Range: <strong className="text-slate-200">{selectedMaterial.meltingRange}</strong></p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <SendToModuleButton
                payload={createPipelinePayloadFromMaterialSpec(selectedMaterial, "Materials Database")}
                onNavigate={onNavigate}
                label="Send to Module ⚡"
                variant="primary"
              />
              <button
                onClick={handleCopySpec}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[#0c1322] border border-[#162032] text-xs font-mono text-slate-300 hover:text-white hover:border-[#243450] transition"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-sky-400" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
              <button
                onClick={() => toggleCompare(selectedMaterial)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-mono border transition ${
                  compareList.some((m) => m.id === selectedMaterial.id)
                    ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/40"
                    : "bg-[#0c1322] border-[#162032] text-slate-300 hover:text-white"
                }`}
              >
                <Scale className="w-3.5 h-3.5" />
                <span>{compareList.some((m) => m.id === selectedMaterial.id) ? "In Comparison" : "Compare"}</span>
              </button>
            </div>
          </div>

          {/* Quick Simulation Lab Pipeline Bar */}
          {/* Chemical Composition Breakdown */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-sky-400 uppercase tracking-widest font-semibold flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                Nominal Chemical Composition (% wt)
              </span>
              <span className="text-[10px] font-mono text-slate-500">Balance: Matrix element</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(selectedMaterial.composition).map(([elem, pct]) => (
                <div
                  key={elem}
                  className="px-2.5 py-1 bg-[#0c1322] rounded-lg border border-[#162032] font-mono text-xs flex items-center gap-2 shadow-sm"
                >
                  <span className="font-bold text-white">{elem}</span>
                  <span className="text-sky-400 font-semibold">
                    {typeof pct === "object" && pct !== null
                      ? `${(pct as any).min}-${(pct as any).max}%`
                      : `${pct}%`}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Mechanical & Physical Properties Grid */}
          <div className="p-4 bg-[#0c1322] rounded-xl border border-[#162032] space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-widest font-semibold block">
                Mechanical & Physical Performance
              </span>
              <span className="text-xs font-mono text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                {selectedMaterial.hardness}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
              <div className="p-2.5 bg-[#090e18] rounded-lg border border-[#162032]">
                <span className="text-slate-400 text-[10px]">Yield Strength (σy)</span>
                <div className="text-base font-bold text-emerald-400 mt-0.5">
                  {selectedMaterial.yieldStrength} <span className="text-xs font-normal text-slate-400">MPa</span>
                </div>
              </div>
              <div className="p-2.5 bg-[#090e18] rounded-lg border border-[#162032]">
                <span className="text-slate-400 text-[10px]">Tensile Strength (UTS)</span>
                <div className="text-base font-bold text-white mt-0.5">
                  {selectedMaterial.tensileStrength} <span className="text-xs font-normal text-slate-400">MPa</span>
                </div>
              </div>
              <div className="p-2.5 bg-[#090e18] rounded-lg border border-[#162032]">
                <span className="text-slate-400 text-[10px]">Young&apos;s Modulus (E)</span>
                <div className="text-base font-bold text-cyan-400 mt-0.5">
                  {selectedMaterial.youngsModulus} <span className="text-xs font-normal text-slate-400">GPa</span>
                </div>
              </div>
              <div className="p-2.5 bg-[#090e18] rounded-lg border border-[#162032]">
                <span className="text-slate-400 text-[10px]">Density (ρ)</span>
                <div className="text-base font-bold text-amber-400 mt-0.5">
                  {selectedMaterial.density} <span className="text-xs font-normal text-slate-400">g/cm³</span>
                </div>
              </div>
            </div>

            {/* Additional Physical Properties */}
            <div className="grid grid-cols-3 gap-2.5 text-xs font-mono pt-1">
              <div className="p-2 bg-[#090e18] rounded-lg border border-[#162032]">
                <span className="text-slate-500 text-[10px] block">Elongation at Break (A5)</span>
                <span className="font-bold text-sky-300">{selectedMaterial.elongation}%</span>
              </div>
              <div className="p-2 bg-[#090e18] rounded-lg border border-[#162032]">
                <span className="text-slate-500 text-[10px] block">Specific Strength</span>
                <span className="font-bold text-indigo-300">
                  {(selectedMaterial.yieldStrength / selectedMaterial.density).toFixed(1)} kN·m/kg
                </span>
              </div>
              <div className="p-2 bg-[#090e18] rounded-lg border border-[#162032]">
                <span className="text-slate-500 text-[10px] block">Thermal Conductivity</span>
                <span className="font-bold text-orange-300">
                  {selectedMaterial.thermalConductivity ?? "—"} W/(m·K)
                </span>
              </div>
            </div>
          </div>

          {/* Microstructure Summary */}
          <div className="p-3.5 bg-[#0c1322] rounded-xl border border-[#162032] space-y-1.5">
            <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-sky-400" />
              Microstructure & Constituent Phases
            </span>
            <p className="text-xs text-slate-200 leading-relaxed font-sans">
              {selectedMaterial.microstructure}
            </p>
          </div>

          {/* Heat Treatment Table */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono text-sky-400 uppercase tracking-widest font-semibold flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5 text-sky-400" />
              Standard Heat Treatment Schedules
            </span>
            <div className="overflow-x-auto rounded-xl border border-[#162032]">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#0c1322] text-slate-400 border-b border-[#162032]">
                  <tr>
                    <th className="p-2.5">Process</th>
                    <th className="p-2.5">Temperature</th>
                    <th className="p-2.5">Cooling Medium</th>
                    <th className="p-2.5">Resulting Hardness / Structure</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#162032] text-[11px]">
                  {selectedMaterial.heatTreatments.map((ht, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02] bg-[#090e18]">
                      <td className="p-2.5 font-bold text-white">{ht.name}</td>
                      <td className="p-2.5 text-sky-400">{ht.temperature}</td>
                      <td className="p-2.5 text-cyan-400">{ht.cooling}</td>
                      <td className="p-2.5 text-emerald-400">{ht.resultingHardness}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Applications & Failure Risks */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
            <div className="p-3.5 bg-[#0c1322] rounded-xl border border-[#162032] space-y-2">
              <div className="flex items-center gap-1.5 text-sky-400 font-bold font-mono text-[10px] uppercase tracking-wider">
                <Wrench className="w-3.5 h-3.5" />
                Common Engineering Applications
              </div>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {selectedMaterial.applications.map((app, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 bg-[#090e18] text-slate-200 rounded-md text-[11px] border border-[#162032]"
                  >
                    {app}
                  </span>
                ))}
              </div>
            </div>

            <div className="p-3.5 bg-[#0c1322] rounded-xl border border-[#162032] space-y-2">
              <div className="flex items-center gap-1.5 text-rose-400 font-bold font-mono text-[10px] uppercase tracking-wider">
                <AlertTriangle className="w-3.5 h-3.5" />
                Metallurgical Failure Risks & Sensitivities
              </div>
              <div className="space-y-1.5 mt-1 text-[11px] text-slate-300">
                {selectedMaterial.failureRisks.map((risk, idx) => (
                  <div key={idx} className="flex items-start gap-1.5">
                    <span className="text-rose-400 font-bold">•</span>
                    <span>{risk}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Alloy Comparison Modal / Drawer */}
      {isCompareOpen && (
        <AccessibleModal
          open
          onClose={() => setIsCompareOpen(false)}
          label="Compare materials"
          overlayClassName="bg-black/80 backdrop-blur-sm p-4"
          panelClassName="bg-[#090e18] border border-[#162032] rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
        >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-[#162032] bg-[#0c1322]">
              <div className="flex items-center gap-2 text-indigo-400 font-mono text-sm font-bold">
                <Scale className="w-4 h-4" />
                <span>Side-by-Side Metallurgical Alloy Comparison ({compareList.length} Selected)</span>
              </div>
              <button
                onClick={() => setIsCompareOpen(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body: Comparison Table */}
            <div className="p-5 overflow-y-auto flex-1 space-y-5">
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono border-collapse">
                  <thead>
                    <tr className="border-b border-[#162032]">
                      <th className="p-3 text-left text-slate-500 bg-[#0c1322] w-44">Property / Metric</th>
                      {compareList.map((mat) => (
                        <th key={mat.id} className="p-3 text-left text-white bg-[#0c1322]">
                          <div className="font-bold text-sm text-sky-400">{mat.name}</div>
                          <div className="text-[10px] text-slate-400">{mat.standard}</div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#162032]">
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Category</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-slate-200 font-semibold">{m.category}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Yield Strength (σy)</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-emerald-400 font-bold text-sm">{m.yieldStrength} MPa</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Tensile Strength (UTS)</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-white font-bold">{m.tensileStrength} MPa</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Young&apos;s Modulus (E)</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-cyan-400 font-bold">{m.youngsModulus} GPa</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Density (ρ)</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-amber-400 font-bold">{m.density} g/cm³</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Specific Strength (σy/ρ)</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-indigo-400 font-bold">
                          {(m.yieldStrength / m.density).toFixed(1)} kN·m/kg
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Elongation at Break</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-sky-300">{m.elongation}%</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Hardness</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-slate-300">{m.hardness}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Thermal Conductivity</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-orange-300">{m.thermalConductivity ?? "—"} W/(m·K)</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Melting Range</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-slate-300">{m.meltingRange}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 text-slate-400 font-bold bg-[#0c1322]/50">Key Applications</td>
                      {compareList.map((m) => (
                        <td key={m.id} className="p-3 text-slate-300 text-[11px]">
                          <ul className="list-disc pl-4 space-y-0.5">
                            {m.applications.slice(0, 3).map((app, i) => (
                              <li key={i}>{app}</li>
                            ))}
                          </ul>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-[#162032] bg-[#0c1322] flex justify-end">
              <button
                onClick={() => setIsCompareOpen(false)}
                className="px-4 py-2 rounded-lg bg-sky-500 text-slate-950 font-bold font-mono text-xs hover:bg-sky-400 transition"
              >
                Close Comparison
              </button>
            </div>
        </AccessibleModal>
      )}

      {/* Composition editor for the shared active specimen (folded in from the former Composition Editor module) */}
      <section id="database-composition-editor" aria-label="Composition editor">
        <AlloyBuilder onNavigate={onNavigate} />
      </section>
    </div>
  );
};
