"""Bounded Module SDK contract for the local Materials Database view."""

from typing import Mapping, Tuple

from module_contract import (
    FORBIDDEN_CLAIM_KEYS,
    OWNER_UNASSIGNED,
    PENDING_ORACLE_CEILING,
    Authority,
    Evidence,
    InputField,
    Lifecycle,
    ModuleContract,
    Operation,
    Oracle,
    OutputSchema,
    TestRefs,
    View,
)


CONTRACT_VERSION = "0.1.0"

_CATEGORIES = (
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
)
_SORT_FIELDS = ("yield", "tensile", "specific_strength", "modulus", "density", "name")
_SORT_ORDERS = ("desc", "asc")
_TRANSFER_TARGETS = ("3d-distortion-lab", "phase-diagram")
_HEATMAP_MODES = ("alloy-elements", "element-property-binned")
_HEATMAP_PROPERTIES = (
    "yieldStrength", "tensileStrength", "youngsModulus", "density", "specificStrength",
    "elongation", "thermalConductivity",
)
_ALLOYING_ELEMENTS = (
    "C", "Cr", "Ni", "Mo", "Ti", "Al", "Cu", "V", "Mn", "Si", "Mg", "W", "Co", "Nb", "Zr", "Fe",
)
_HEATMAP_SORT_FIELDS = ("property", "element", "category", "name")
_HEATMAP_PALETTES = ("viridis", "plasma", "turbo", "emerald", "amber-flame")

_BROWSER_REASON = (
    "MaterialsDatabaseView reads the bundled MATERIALS_DATABASE and mutates browser-local React/UI state; "
    "it has no server route or operation deadline."
)


def _local_operation(
    operation_id: str,
    *,
    fields: Tuple[InputField, ...] = (),
    undeclared: Tuple[str, ...] = (),
    outputs: Tuple[str, ...],
) -> Operation:
    return Operation(
        id=operation_id,
        route=None,
        method=None,
        authority=Authority(kind="browser-local", timeout_ms=None, exception_reason=_BROWSER_REASON),
        input=fields,
        undeclared_input=undeclared,
        output=OutputSchema(fields=outputs, status_key=None),
    )


DATABASE_OPERATIONS: Tuple[Operation, ...] = (
    _local_operation(
        "search-catalog",
        undeclared=("searchQuery",),
        outputs=("filteredMaterials", "visibleCount"),
    ),
    _local_operation(
        "filter-by-category",
        fields=(
            InputField(
                key="selectedCategory",
                label="Catalog category filter",
                unit=None,
                quantity_kind="local-catalog-filter",
                min=None,
                max=None,
                default="All",
                required=False,
                enum=_CATEGORIES,
                value_type="enum",
                note="These are the exact category pills in MaterialsDatabaseView; the field filters local rows only.",
            ),
        ),
        outputs=("filteredMaterials", "visibleCount"),
    ),
    _local_operation(
        "filter-by-min-yield-strength",
        fields=(
            InputField(
                key="minYield", label="Minimum yield-strength filter", unit="MPa",
                quantity_kind="local-catalog-filter", min=None, max=None, default=0,
                required=False, step=50,
                note="UI state default and slider step; slider attributes do not establish material validity bounds.",
            ),
        ),
        outputs=("filteredMaterials", "visibleCount"),
    ),
    _local_operation(
        "filter-by-min-modulus",
        fields=(
            InputField(
                key="minModulus", label="Minimum Young's-modulus filter", unit="GPa",
                quantity_kind="local-catalog-filter", min=None, max=None, default=40,
                required=False, step=10,
                note="UI state default and slider step; slider attributes do not establish material validity bounds.",
            ),
        ),
        outputs=("filteredMaterials", "visibleCount"),
    ),
    _local_operation(
        "filter-by-max-density",
        fields=(
            InputField(
                key="maxDensity", label="Maximum density filter", unit="g/cm^3",
                quantity_kind="local-catalog-filter", min=None, max=None, default=17.0,
                required=False, step=0.2,
                note=(
                    "The visible density slider edits maxDensity (value=maxDensity, setter=setMaxDensity); "
                    "its state default is 17.0 and step is 0.2. minDensity remains fixed at 1.5 here. "
                    "Slider attributes do not establish material validity bounds."
                ),
            ),
        ),
        outputs=("filteredMaterials", "visibleCount"),
    ),
    _local_operation(
        "reset-property-range-filters",
        outputs=("minYield", "maxYield", "minModulus", "maxModulus", "minDensity", "maxDensity"),
    ),
    _local_operation(
        "toggle-property-filter-panel",
        outputs=("showFilters",),
    ),
    _local_operation(
        "switch-view-mode",
        fields=(
            InputField(
                key="activeTab", label="Database view mode", unit=None, quantity_kind="local-view-mode",
                min=None, max=None, default="split", enum=("split", "heatmap", "catalog"), value_type="enum",
            ),
        ),
        outputs=("activeView",),
    ),
    _local_operation(
        "sort-catalog",
        fields=(
            InputField(
                key="sortBy", label="Catalog sort key", unit=None, quantity_kind="local-sort-control",
                min=None, max=None, default="yield", enum=_SORT_FIELDS, value_type="enum",
            ),
            InputField(
                key="sortOrder", label="Catalog sort direction", unit=None, quantity_kind="local-sort-control",
                min=None, max=None, default="desc", enum=_SORT_ORDERS, value_type="enum",
            ),
        ),
        outputs=("sortedMaterials",),
    ),
    _local_operation(
        "select-material-record",
        undeclared=("material",),
        outputs=("selectedMaterial",),
    ),
    _local_operation(
        "toggle-comparison-record",
        undeclared=("material",),
        outputs=("compareList",),
    ),
    _local_operation(
        "open-comparison-drawer",
        outputs=("isCompareOpen",),
    ),
    _local_operation(
        "close-comparison-drawer",
        outputs=("isCompareOpen",),
    ),
    _local_operation(
        "copy-selected-record",
        outputs=("clipboardWriteAttempt", "optimisticCopyFeedback"),
    ),
    _local_operation(
        "export-catalog-json",
        outputs=("fullCatalogJsonDownload",),
    ),
    _local_operation(
        "open-transfer-picker",
        outputs=("transferPickerOpen",),
    ),
    _local_operation(
        "dispatch-material-to-module",
        fields=(
            InputField(
                key="targetId", label="Transfer destination", unit=None, quantity_kind="module-navigation-target",
                min=None, max=None, default="3d-distortion-lab", enum=_TRANSFER_TARGETS, value_type="enum",
                note="Exact destination IDs rendered by SendToModuleModal for this transfer flow.",
            ),
        ),
        outputs=("pipelineMaterialEvent", "navigationTarget"),
    ),
)


HEATMAP_OPERATIONS: Tuple[Operation, ...] = (
    _local_operation(
        "render-heatmap",
        undeclared=("materials", "selectedMaterial"),
        outputs=("displayedMaterials", "svgPlot"),
    ),
    _local_operation(
        "set-heatmap-mode",
        fields=(InputField(
            key="heatmapMode", label="D3 plot mode", unit=None, quantity_kind="local-view-mode",
            min=None, max=None, default="alloy-elements", enum=_HEATMAP_MODES, value_type="enum",
        ),),
        outputs=("heatmapMode", "svgPlot"),
    ),
    _local_operation(
        "set-heatmap-property",
        fields=(InputField(
            key="selectedPropertyKey", label="Heatmap property", unit=None, quantity_kind="catalog-property-key",
            min=None, max=None, default="yieldStrength", enum=_HEATMAP_PROPERTIES, value_type="enum",
        ),),
        outputs=("selectedPropertyKey", "svgPlot"),
    ),
    _local_operation(
        "set-heatmap-element",
        fields=(InputField(
            key="selectedElement", label="Focused alloying element", unit=None, quantity_kind="element-symbol",
            min=None, max=None, default="Cr", enum=_ALLOYING_ELEMENTS, value_type="enum",
            note="The select options are the component's alloying-element list; plot-axis clicks choose from elements present in the current data.",
        ),),
        outputs=("selectedElement", "svgPlot"),
    ),
    _local_operation(
        "sort-heatmap-alloys",
        fields=(InputField(
            key="sortBy", label="Heatmap sort key", unit=None, quantity_kind="local-sort-control",
            min=None, max=None, default="property", enum=_HEATMAP_SORT_FIELDS, value_type="enum",
            note="This selector is rendered only in alloy-elements mode; sortAsc is initialized false but has no current UI setter.",
        ),),
        outputs=("displayedMaterials", "svgPlot"),
    ),
    _local_operation(
        "set-heatmap-palette",
        fields=(InputField(
            key="colorPalette", label="D3 color palette", unit=None, quantity_kind="local-plot-style",
            min=None, max=None, default="viridis", enum=_HEATMAP_PALETTES, value_type="enum",
        ),),
        outputs=("colorPalette", "svgPlot"),
    ),
    _local_operation(
        "select-heatmap-element-from-axis",
        undeclared=("elem",),
        outputs=("selectedElement", "svgPlot"),
    ),
    _local_operation(
        "select-heatmap-property-from-axis",
        undeclared=("prop",),
        outputs=("selectedPropertyKey", "svgPlot"),
    ),
    _local_operation(
        "select-composition-cell",
        undeclared=("mat", "elem"),
        outputs=("selectedMaterial", "selectedElement"),
    ),
    _local_operation(
        "select-binned-bucket",
        undeclared=("b",),
        outputs=("selectedMaterial",),
    ),
    _local_operation(
        "select-scatter-point",
        undeclared=("mat",),
        outputs=("selectedMaterial",),
    ),
    _local_operation(
        "inspect-composition-cell",
        undeclared=("mat", "elem", "wt"),
        outputs=("hoveredCell", "xLabel", "yLabel", "value", "unit", "material", "extraInfo", "xPos", "yPos"),
    ),
    _local_operation(
        "inspect-binned-cell",
        undeclared=("b",),
        outputs=("hoveredCell", "xLabel", "yLabel", "value", "extraInfo", "xPos", "yPos"),
    ),
    _local_operation(
        "clear-heatmap-tooltip",
        outputs=("hoveredCell",),
    ),
    _local_operation(
        "export-heatmap-svg",
        outputs=("source", "blob", "url", "download"),
    ),
)


def build_database_contract(seed: Mapping[str, str]) -> ModuleContract:
    """Build the source-bounded contract from the unchanged database seed row."""
    return ModuleContract(
        id=seed["id"],
        version=CONTRACT_VERSION,
        owner=OWNER_UNASSIGNED,
        workspace=seed["workspace"],
        label=seed["label"],
        description=seed["description"],
        next=seed["next"],
        maturity=seed["scope"],
        navigation="listed",
        view=View(component=seed["viewComponent"], export=seed["viewExport"]),
        evidence=Evidence(
            emits=(),
            ceiling=PENDING_ORACLE_CEILING,
            forbidden_claims=FORBIDDEN_CLAIM_KEYS,
            note=(
                "No numerical or provenance oracle is declared for this catalog view. Displayed handbook-style "
                "properties and downstream composition-based profiles remain screening material; browsing or "
                "transferring a record does not establish source applicability, calibration, or physical validation."
            ),
        ),
        tests=TestRefs(
            oracle=Oracle(status="pending"),
            schema="python/test_module_contract_database.py",
            docs="docs/modules/database.md",
        ),
        migration_state="contracted",
        operations=DATABASE_OPERATIONS + HEATMAP_OPERATIONS,
        lifecycle=Lifecycle(background_work="none", resources=()),
        legacy_notes=(
            "This module reads the statically imported MATERIALS_DATABASE array and performs filtering, sorting, "
            "selection, comparison, clipboard copy, JSON download, and transfer-payload preparation in the browser. "
            "Outputs name local view effects and transfer state; this is not an API request/response surface.",
            "The trimmed, lowercased searchQuery checks material name, standard, category, microstructure, application text, and composition element symbols. Category filtering is exact. Yield strength and Young's modulus are filtered by both min and max state; density is also filtered by both min and max. Only minYield, minModulus, and maxDensity have visible sliders; maxYield, maxModulus, and minDensity remain at their initialized values unless the reset action writes them. Slider limits and steps are control settings, not a material validity domain.",
            "MaterialSpec stores nominal scalar or min/max composition entries and property values, but has no "
            "per-property source citation, condition/temper, applicability, uncertainty, or confidence fields. The "
            "catalog header no longer claims calibrated compositions; no record-level evidence link or validation proof exists.",
            "Selection and comparison callbacks receive MaterialSpec records from local catalog rows. Since the SDK "
            "scalar schema cannot describe that nested record/map, these actions record the actual 'material' input "
            "as undeclared rather than inventing a record-ID endpoint or object schema.",
            "createPipelinePayloadFromMaterialSpec preserves originalComposition and marks composition as nominal "
            "or range-midpoint, while normalizing composition and deriving kinetic, hardness, and XRD profiles. "
            "The downstream bridge states that source property values/confidence are not promoted and derived "
            "properties remain estimates. Missing Poisson ratio also receives a code fallback in the pipeline; "
            "that fallback is software behavior, not a database measurement.",
            "The transfer picker presents the LPBF wizard and Phase Diagram as destinations. "
            "Dispatch stores the payload through the browser pipeline utility, then navigates after a 350 ms "
            "setTimeout. This is a local cross-module handoff, not provider/server execution or LPBF acceptance.",
            "The comparison list initially contains catalog entries at indexes 0 and 5; clicking toggles membership "
            "and additions stop at four entries. The category and view-mode enums below describe the actual visible "
            "controls, not material-property validity classes.",
            "The property-filter panel has a local showFilters toggle. The comparison drawer opens only when the "
            "compare list is nonempty and closes from its modal callback or either close button.",
            "Copy calls navigator.clipboard.writeText without awaiting or catching its promise, then immediately "
            "sets copied=true and clears that optimistic feedback after 2000 ms. The UI feedback therefore records "
            "an attempted copy, not confirmed clipboard success; permission/API failure is not handled here.",
            "Export serializes the full MATERIALS_DATABASE array, independent of active filters; it creates an object "
            "URL, clicks a download link, then revokes the URL in the same handler. Lifecycle has no timeout/object-URL "
            "resource kind; these are noted as short UI effects rather than invented lifecycle resources.",
            "MaterialsPropertyHeatmapD3 is mounted only while activeTab is \"split\" or \"heatmap\"; catalog mode unmounts it. Its ResizeObserver disconnects on effect dependency change and unmount. The D3-render effect has no cleanup function: redraw removes prior SVG descendants, while normal unmount removes the child DOM. If displayedMaterials becomes empty, that effect returns before clearing the prior SVG, so a previous plot can remain visible until a later nonempty redraw or unmount.",
            "The child props are materials: MaterialSpec[], selectedMaterial: MaterialSpec, onSelectMaterial(MaterialSpec), categories: string[], activeCategory: string, and optional onSelectCategory(string). The parent passes filteredMaterials and selectedMaterial; the two nested record props are recorded as undeclared on render-heatmap because the scalar SDK schema cannot represent them. Callback effects are captured by selection operations. categories, activeCategory, and onSelectCategory are passed but unused by this child. Child sortAsc is initialized false and searchAlloy empty, but neither has a current UI setter; do not report either as a user-editable control. Heatmap modes, property keys, element selector options, sort keys, and palette options are the source-defined control values only.",
            "Heatmap cell/axis interactions update local selected material, element, or property state; no plot click submits a calculation. The selection/hover operation inputs use the actual closure values mat, elem, wt, b, prop, and cell where applicable; their nested D3 data shapes are not promoted into a fabricated stable schema. Composition cells show catalog wt-percent values, binned cells summarize current catalog records and select the first member. These are descriptive visualizations of bundled records, not independent measurements, fitted validation, or a physical oracle.",
            "The child SVG export serializes the current SVG into a Blob, creates an object URL, clicks a temporary download anchor named from heatmapMode and selectedPropertyKey, then revokes the URL synchronously. These output names describe transient browser transport effects, not a returned API object. ResizeObserver, timers, and object URLs have no matching lifecycle resource kind in the schema vocabulary and are documented here rather than mislabeled as raf/interval/three/fetch.",
            "No fetch, worker, solver, scheduled job, or source download is initiated by this view or its D3 child. The nested comparison and transfer dialogs are UI children, not background work.",
        ),
        source_refs=(
            "src/components/MaterialsDatabaseView.tsx:36-111#filteredMaterials",
            "src/components/MaterialsDatabaseView.tsx:122-143#handleCopySpec",
            "src/components/MaterialsDatabaseView.tsx:60-72#categories",
            "src/components/MaterialsDatabaseView.tsx:236-338#Property Sliders",
            "src/components/MaterialsDatabaseView.tsx:230-245#setShowFilters(!showFilters)",
            "src/components/MaterialsDatabaseView.tsx:250-264#Sort:",
            "src/components/MaterialsDatabaseView.tsx:336-346#Maximum Density (ρ)",
            "src/components/MaterialsDatabaseView.tsx:153-153#Chemical compositions, tensile",
            "src/components/MaterialsDatabaseView.tsx:58-58#compareList",
            "src/components/MaterialsDatabaseView.tsx:113-118#compareList.length < 4",
            "src/components/MaterialsDatabaseView.tsx:373-377#MaterialsPropertyHeatmapD3",
            "src/components/MaterialsDatabaseView.tsx:405-405#setSelectedMaterial(mat)",
            "src/components/MaterialsDatabaseView.tsx:486-486#createPipelinePayloadFromMaterialSpec",
            "src/components/MaterialsDatabaseView.tsx:202-202#setIsCompareOpen(true)",
            "src/components/MaterialsDatabaseView.tsx:674-695#setIsCompareOpen(false)",
            "src/components/MaterialsPropertyHeatmapD3.tsx::MaterialsPropertyHeatmapD3",
            "src/components/MaterialsPropertyHeatmapD3.tsx::HEATMAP_PROPERTIES",
            "src/components/MaterialsPropertyHeatmapD3.tsx::ALLOYING_ELEMENTS",
            "src/components/MaterialsPropertyHeatmapD3.tsx:252-275#observer.disconnect()",
            "src/components/MaterialsPropertyHeatmapD3.tsx:277-277#useEffect(() => {",
            "src/components/MaterialsPropertyHeatmapD3.tsx:645-656#URL.revokeObjectURL(url)",
            "src/components/MaterialsPropertyHeatmapD3.tsx:820-840#hoveredCell",
            "src/types.ts:28-59#MaterialSpec",
            "src/data/materialsDatabase.ts:1-28#MATERIALS_DATABASE",
            "src/utils/materialDataPipeline.ts:666-715#createPipelinePayloadFromMaterialSpec",
            "src/utils/materialDataPipeline.ts:718-729#setActivePipelineMaterial",
            "src/components/SendToModuleButton.tsx:6-12#SendToModuleButtonProps",
            "src/components/SendToModuleModal.tsx:47-62#handleDispatch",
            "src/components/SendToModuleModal.tsx:63-132#targets",
            "src/utils/materialDataPipeline.ts:6-11#ModuleTargetId",
            "src/services/materialContextBridge.ts:47-70#applyIdentity",
            "src/services/materialContextBridge.ts:91-91#subscribeToPipelineMaterial",
        ),
        seed_derived=("label", "description", "next", "maturity"),
    )
