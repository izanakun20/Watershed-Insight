/* ===================================================================
   SIH 26015 — Watershed Command Centre Platform
   Main Application JavaScript
   Vanilla JS SPA with Leaflet map integration
   =================================================================== */

// =============================================================
// API Client
// =============================================================
const API = {
    async get(path) {
        const res = await fetch(path);
        if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
        return res.json();
    },
    async postForm(path, formData) {
        const res = await fetch(path, { method: 'POST', body: formData });
        if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
        return res.json();
    }
};

// =============================================================
// State
// =============================================================
const state = {
    currentView: null,
    dashboardData: null,
    watershedInfo: null,
    records: [],
    layersCatalog: [],
    changeData: null,
    hotspots: [],
    mapInitialized: false,
    fieldMapInitialized: false,
};

// =============================================================
// Router
// =============================================================
function initRouter() {
    // Nav link clicks
    document.querySelectorAll('.top-nav__link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            navigateTo(view);
        });
    });

    // Handle hash changes
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.replace('#', '') || 'dashboard';
        navigateTo(hash, false);
    });

    // Initial route
    const initial = window.location.hash.replace('#', '') || 'dashboard';
    navigateTo(initial, false);
}

function navigateTo(viewName, pushHash = true) {
    if (state.currentView === viewName) return;

    // Hide all views
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

    // Show target view
    const target = document.getElementById(`view-${viewName}`);
    if (target) {
        target.classList.add('active');
    } else {
        document.getElementById('view-dashboard').classList.add('active');
        viewName = 'dashboard';
    }

    // Update nav links
    document.querySelectorAll('.top-nav__link').forEach(l => {
        l.classList.toggle('active', l.dataset.view === viewName);
    });

    state.currentView = viewName;
    if (pushHash) window.location.hash = viewName;

    // Initialize view content
    onViewActivated(viewName);
}

function onViewActivated(viewName) {
    switch (viewName) {
        case 'dashboard': renderDashboard(); break;
        case 'map': initMapView(); break;
        case 'field': initFieldView(); break;
        case 'analysis': renderAnalysis(); break;
        case 'reports': renderReports(); break;
    }
}

// =============================================================
// Dashboard View
// =============================================================
async function renderDashboard() {
    const container = document.getElementById('dashboard-content');

    if (state.dashboardData) {
        buildDashboardUI(container, state.dashboardData);
        return;
    }

    container.innerHTML = '<div class="loading-spinner">Loading dashboard data...</div>';

    try {
        const [dashboard, info] = await Promise.all([
            API.get('/api/dashboard/summary'),
            API.get('/api/watershed/info'),
        ]);
        state.dashboardData = dashboard;
        state.watershedInfo = info;
        buildDashboardUI(container, dashboard);
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Error loading dashboard: ${err.message}</p></div>`;
    }
}

function buildDashboardUI(container, data) {
    const ws = data.watershed || {};
    const kpis = data.kpis || {};
    const recent = data.recent_records || [];
    const hotspots = data.hotspots || [];
    const catCounts = data.category_counts || {};

    container.innerHTML = `
        <div class="map-layout">
            <aside class="map-sidebar" id="dashboard-sidebar" style="width: 400px;">
                <!-- Watershed Header -->
                <div class="map-sidebar__header" style="background: var(--surface-container-high);">
                    <div class="map-sidebar__title">${ws.name || 'Gundlakamma Watershed'}</div>
                    <div class="map-sidebar__subtitle">${ws.district || 'Prakasam'}, ${ws.state || 'Andhra Pradesh'} · ~${ws.approx_area_km2 || '—'} km²</div>
                </div>

                <!-- KPI Cards -->
                <div class="map-sidebar__section" style="padding-bottom: 0;">
                    <div class="kpi-grid" id="kpi-grid" style="grid-template-columns: 1fr 1fr; margin-bottom: var(--unit-md);">
                        ${buildKPICard('park', 'green', 'Mean NDVI (2026)', kpis.mean_ndvi != null ? kpis.mean_ndvi.toFixed(3) : '—', '')}
                        ${buildKPICard('water_drop', 'blue', 'Water Coverage', kpis.water_coverage_pct != null ? kpis.water_coverage_pct.toFixed(1) + '%' : '—', '')}
                        ${buildKPICard('trending_up', 'green', 'Veg Improved', kpis.vegetation_improved_pct != null ? kpis.vegetation_improved_pct.toFixed(1) + '%' : '—', '')}
                        ${buildKPICard('trending_down', 'orange', 'Veg Degraded', kpis.vegetation_degraded_pct != null ? kpis.vegetation_degraded_pct.toFixed(1) + '%' : '—', '')}
                        ${buildKPICard('photo_camera', 'blue', 'Field Records', kpis.total_field_records || 0, '')}
                        ${buildKPICard('warning', 'red', 'Flagged Spots', kpis.flagged_locations || 0, '')}
                    </div>
                </div>

                <!-- Recent Observations -->
                <div class="map-sidebar__section">
                    <div class="map-sidebar__section-title" style="display:flex; justify-content:space-between; align-items:center;">
                        Recent Observations
                        <a href="#field" style="color:var(--primary); font-size:12px; text-decoration:none; text-transform:none;">View All</a>
                    </div>
                    <div class="records-list" id="dashboard-records">
                        ${recent.length === 0 ? '<p style="color: var(--on-surface-variant);">No records found.</p>' : ''}
                        ${recent.slice(0, 3).map(r => buildRecordItem(r)).join('')}
                    </div>
                </div>

                <!-- Change Hotspots -->
                <div class="map-sidebar__section">
                    <div class="map-sidebar__section-title" style="display:flex; justify-content:space-between; align-items:center;">
                        Change Hotspots
                        <a href="#analysis" style="color:var(--primary); font-size:12px; text-decoration:none; text-transform:none;">Analysis</a>
                    </div>
                    <div class="card" style="padding: 0;">
                        ${hotspots.length === 0 ? '<p style="color: var(--on-surface-variant); padding: 8px;">No hotspots detected.</p>' : ''}
                        ${hotspots.slice(0, 3).map(h => `
                            <div class="hotspot-item" style="border-bottom: 1px solid var(--outline-variant); padding: 8px 12px; cursor: pointer;" onclick="if(window.dashboardMap) { window.dashboardMap.setView([${h.latitude}, ${h.longitude}], 15); }">
                                <div class="hotspot-item__marker" style="background: ${h.type === 'improvement' ? 'var(--success)' : 'var(--error)'}"></div>
                                <div class="hotspot-item__coords">${h.latitude.toFixed(4)}°N, ${h.longitude.toFixed(4)}°E</div>
                                <span class="badge ${h.type === 'improvement' ? 'badge--improvement' : 'badge--degradation'}">${h.type}</span>
                                <div class="hotspot-item__value" style="color: ${h.value > 0 ? 'var(--success)' : 'var(--error)'}">${h.value > 0 ? '+' : ''}${h.value.toFixed(3)}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Data Provenance -->
                <div class="map-sidebar__section" style="border-bottom: none;">
                    <div class="disclaimer">
                        <div class="disclaimer__title">Data Provenance & Disclaimers</div>
                        <ul class="disclaimer__list" style="margin-bottom: 0;">
                            <li>Sentinel-2 L2A imagery (10m)</li>
                            <li>Approximate AOI boundary</li>
                            <li>DRISHTI records are mock data</li>
                        </ul>
                    </div>
                </div>
            </aside>
            <div class="map-container" id="dashboard-map-container">
                <div id="dashboard-map" style="width: 100%; height: 100%; background: #e2e8f0;"></div>
            </div>
        </div>
    `;

    // Initialize Dashboard Map
    initDashboardMap(data);
}

// -------------------------------------------------------------------
// Dashboard Map Initialization
// -------------------------------------------------------------------
let dashboardMap = null;
let dashboardMarkers = L.layerGroup();

function initDashboardMap(data) {
    if (dashboardMap) {
        dashboardMap.remove();
        dashboardMap = null;
    }

    dashboardMap = L.map('dashboard-map', {
        zoomControl: false // Move zoom control to bottom right
    }).setView([15.7, 79.9], 10);

    L.control.zoom({ position: 'bottomright' }).addTo(dashboardMap);

    // Add satellite imagery as base
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 18,
    }).addTo(dashboardMap);

    // Load watershed boundary
    fetch('/data/downloaded_data/bhuvan/gundlakamma_basin_approx.geojson')
        .then(r => r.json())
        .then(geoJson => {
            const boundaryLayer = L.geoJSON(geoJson, {
                style: {
                    color: '#0ea5e9',
                    weight: 3,
                    fillOpacity: 0.1,
                    dashArray: '5, 5'
                }
            }).addTo(dashboardMap);
            dashboardMap.fitBounds(boundaryLayer.getBounds());
        })
        .catch(e => console.error('Error loading watershed boundary:', e));

    // Expose map globally for inline onclick handlers in the sidebar
    window.dashboardMap = dashboardMap;
    setTimeout(() => {
        if (dashboardMap) dashboardMap.invalidateSize();
    }, 100);

    // Load and plot DRISHTI markers
    fetch('/api/drishti/records')
        .then(r => r.json())
        .then(res => {
            const records = res.records || [];
            dashboardMarkers.clearLayers();

            records.forEach(record => {
                if (record.latitude && record.longitude) {
                    // Create popup content
                    const isConsistent = record.crosscheck?.is_consistent;
                    const crosscheckBadge = isConsistent 
                        ? `<span class="badge badge--consistent"><span class="material-symbols-outlined" style="font-size:12px;">check_circle</span> Verified by Satellite</span>`
                        : `<span class="badge badge--inconsistent"><span class="material-symbols-outlined" style="font-size:12px;">warning</span> Discrepancy Found</span>`;
                    
                    let photoSrc = '';
                    if (record.photo_filename) {
                        // Extract just the basename in case it's a full path
                        const fname = record.photo_filename.split(/[\\/]/).pop();
                        photoSrc = `/api/drishti/photos/${fname}`;
                    } else if (record.photo_url) {
                        const match = record.photo_url.match(/\/api\/drishti\/photos\/(.+)/);
                        if (match) {
                            photoSrc = `/api/drishti/photos/${match[1]}`;
                        } else {
                            photoSrc = record.photo_url;
                        }
                    }

                    const popupHtml = `
                        <div style="min-width: 250px; padding: 4px;">
                            <img src="${photoSrc}" style="width: 100%; height: 120px; object-fit: cover; border-radius: var(--radius-sm); margin-bottom: 8px;">
                            <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">${record.intervention_type}</div>
                            <div style="color: var(--on-surface-variant); font-size: 12px; margin-bottom: 8px;">
                                <span class="badge badge--mock">${record.intervention_stage}</span> · ${new Date(record.timestamp).toLocaleDateString('en-IN')}
                            </div>
                            <div style="font-family: var(--font-data-mono); font-size: 11px; margin-bottom: 8px; color: var(--outline);">
                                ${record.latitude.toFixed(5)}°N, ${record.longitude.toFixed(5)}°E
                            </div>
                            <div style="margin-bottom: 12px;">
                                ${crosscheckBadge}
                            </div>
                            <button class="btn btn--secondary" style="width: 100%; justify-content: center; font-size: 12px;" onclick="window.location.hash = '#reports'">View Full Assessment</button>
                        </div>
                    `;

                    const markerIcon = L.divIcon({
                        className: '',
                        html: `<div style="width:20px;height:20px;background:var(--primary);border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>`,
                        iconSize: [20, 20],
                        iconAnchor: [10, 10],
                    });

                    const marker = L.marker([record.latitude, record.longitude], { icon: markerIcon })
                        .bindPopup(popupHtml, { minWidth: 260, offset: [0, -5] });
                    
                    dashboardMarkers.addLayer(marker);
                }
            });

            dashboardMarkers.addTo(dashboardMap);
        })
        .catch(e => console.error('Error loading DRISHTI markers:', e));
}

function buildKPICard(icon, colorClass, label, value, detail) {
    return `
        <div class="kpi-card">
            <div class="kpi-card__icon kpi-card__icon--${colorClass}">
                <span class="material-symbols-outlined">${icon}</span>
            </div>
            <div class="kpi-card__label">${label}</div>
            <div class="kpi-card__value">${value}</div>
            <div class="kpi-card__detail">${detail}</div>
        </div>
    `;
}

function buildRecordItem(r) {
    const catIcons = {
        'Water Harvesting': 'water_drop',
        'Soil Conservation': 'landscape',
        'Vegetation/Biomass': 'park',
    };
    const catColors = {
        'Water Harvesting': 'var(--info-bg)',
        'Soil Conservation': 'var(--warning-bg)',
        'Vegetation/Biomass': 'var(--success-bg)',
    };
    const catTextColors = {
        'Water Harvesting': 'var(--info-text)',
        'Soil Conservation': 'var(--warning-text)',
        'Vegetation/Biomass': 'var(--success-text)',
    };
    const icon = catIcons[r.intervention_category] || 'location_on';
    const bgColor = catColors[r.intervention_category] || 'var(--surface-container)';
    const textColor = catTextColors[r.intervention_category] || 'var(--on-surface-variant)';
    const date = r.timestamp ? new Date(r.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '';

    const recordId = r.record_id || r.id;
    return `
        <div class="record-item" data-id="${recordId}">
            <div class="record-item__icon" style="background: ${bgColor}; color: ${textColor};">
                <span class="material-symbols-outlined">${icon}</span>
            </div>
            <div class="record-item__content">
                <div class="record-item__title">${r.intervention_type}</div>
                <div class="record-item__subtitle">${r.intervention_stage} · ${date}</div>
            </div>
            <span class="badge badge--mock">Mock</span>
        </div>
    `;
}

// =============================================================
// Map / Monitor View
// =============================================================
let mainMap = null;
let mapLayers = {};
let mapMarkers = [];
let boundsData = null;

async function initMapView() {
    if (state.mapInitialized) {
        if (mainMap) mainMap.invalidateSize();
        return;
    }

    // Initialize map
    mainMap = L.map('map', {
        zoomControl: true,
    }).setView([15.35, 79.65], 10);

    // Base layer
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri',
        maxZoom: 18,
    }).addTo(mainMap);

    // Load bounds data for overlays
    try {
        const res = await fetch('/data/processed_data/web/bounds.json');
        boundsData = await res.json();
    } catch (e) {
        console.warn('Could not load overlay bounds:', e);
        boundsData = {};
    }

    // Setup layers
    await setupMapLayers();

    // Load DRISHTI markers
    await loadDrishtiMarkers(mainMap);

    // Build layer toggles
    buildLayerToggles();

    state.mapInitialized = true;

    // Fit to watershed if available
    try {
        const basinRes = await fetch('/data/downloaded_data/bhuvan/gundlakamma_basin_approx.geojson');
        const basinData = await basinRes.json();
        const basinLayer = L.geoJSON(basinData, {
            style: { color: '#FF7800', weight: 3, fillOpacity: 0.05, dashArray: '8 4' }
        }).addTo(mainMap);
        mapLayers.watershed_boundary = basinLayer;
        mainMap.fitBounds(basinLayer.getBounds(), { padding: [20, 20] });
    } catch (e) {
        console.warn('Could not load basin boundary:', e);
    }
}

async function setupMapLayers() {
    // Image overlays from bounds.json
    const overlayConfig = [
        { key: 'ndvi', file: 'ndvi.png', label: 'NDVI (2026)', opacity: 0.75, defaultOn: false },
        { key: 'ndvi_change', file: 'ndvi_change.png', label: 'NDVI Change', opacity: 0.8, defaultOn: false },
        { key: 'ndwi', file: 'ndwi.png', label: 'NDWI (2026)', opacity: 0.75, defaultOn: false },
        { key: 'water_mask', file: 'water_mask.png', label: 'Water Mask', opacity: 0.8, defaultOn: false },
        { key: 'water_change', file: 'water_change.png', label: 'Water Change', opacity: 0.8, defaultOn: false },
        { key: 'slope', file: 'slope.png', label: 'Slope', opacity: 0.75, defaultOn: false },
    ];

    for (const cfg of overlayConfig) {
        if (boundsData && boundsData[cfg.key]) {
            const layer = L.imageOverlay(`/data/processed_data/web/${cfg.file}`, boundsData[cfg.key], {
                opacity: cfg.opacity,
            });
            mapLayers[cfg.key] = layer;
            if (cfg.defaultOn) layer.addTo(mainMap);
        }
    }

    // Drainage GeoJSON
    try {
        const drainageRes = await fetch('/data/processed_data/drainage_osm_fallback.geojson');
        const drainageData = await drainageRes.json();
        mapLayers.drainage = L.geoJSON(drainageData, {
            style: { color: '#3B82F6', weight: 1.5, opacity: 0.7 }
        });
    } catch (e) {
        // Try the CartoDEM drainage if the OSM one fails
        try {
            const drainageRes = await fetch('/data/processed_data/cartodem_drainage.geojson');
            const drainageData = await drainageRes.json();
            mapLayers.drainage = L.geoJSON(drainageData, {
                style: { color: '#3B82F6', weight: 1.5, opacity: 0.7 }
            });
        } catch (e2) {
            console.warn('Could not load drainage:', e2);
        }
    }

    // Bhuvan LULC WMS
    mapLayers.bhuvan_lulc = L.tileLayer.wms('https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms', {
        layers: 'lulc:AP_LULC50K_1516',
        format: 'image/png',
        transparent: true,
        opacity: 0.6,
    });
}

async function loadDrishtiMarkers(targetMap) {
    try {
        const data = await API.get('/api/drishti/records');
        state.records = data.records || [];

        const catColors = {
            'Water Harvesting': '#3B82F6',
            'Soil Conservation': '#F59E0B',
            'Vegetation/Biomass': '#10B981',
        };

        state.records.forEach(rec => {
            const color = catColors[rec.intervention_category] || '#E74C3C';
            const marker = L.circleMarker([rec.latitude, rec.longitude], {
                radius: 7,
                fillColor: color,
                color: '#FFFFFF',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.85,
            }).addTo(targetMap);

            const record = rec; // alias for popup logic

            const isConsistent = record.crosscheck?.is_consistent;
            const crosscheckBadge = isConsistent 
                ? `<span class="badge badge--consistent"><span class="material-symbols-outlined" style="font-size:12px;">check_circle</span> Verified by Satellite</span>`
                : `<span class="badge badge--inconsistent"><span class="material-symbols-outlined" style="font-size:12px;">warning</span> Discrepancy Found</span>`;
            
            let photoSrc = '';
            if (record.photo_filename) {
                const fname = record.photo_filename.split(/[\\/]/).pop();
                photoSrc = `/api/drishti/photos/${fname}`;
            } else if (record.photo_url) {
                const match = record.photo_url.match(/\/api\/drishti\/photos\/(.+)/);
                if (match) {
                    photoSrc = `/api/drishti/photos/${match[1]}`;
                } else {
                    photoSrc = record.photo_url;
                }
            }

            const popupHtml = `
                <div style="min-width: 250px; padding: 4px;">
                    <img src="${photoSrc}" style="width: 100%; height: 120px; object-fit: cover; border-radius: var(--radius-sm); margin-bottom: 8px;">
                    <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">${record.intervention_type}</div>
                    <div style="color: var(--on-surface-variant); font-size: 12px; margin-bottom: 8px;">
                        <span class="badge badge--mock">${record.intervention_stage}</span> · ${new Date(record.timestamp).toLocaleDateString('en-IN')}
                    </div>
                    <div style="font-family: var(--font-data-mono); font-size: 11px; margin-bottom: 8px; color: var(--outline);">
                        ${record.latitude.toFixed(5)}°N, ${record.longitude.toFixed(5)}°E
                    </div>
                    <div style="margin-bottom: 12px;">
                        ${crosscheckBadge}
                    </div>
                    <button class="btn btn--secondary" style="width: 100%; justify-content: center; font-size: 12px;" onclick="window.location.hash = '#reports'">View Full Assessment</button>
                </div>
            `;

            marker.bindPopup(popupHtml, { minWidth: 260, offset: [0, -5] });

            const recordId = rec.record_id || rec.id;
            marker._recordId = recordId;
            mapMarkers.push(marker);
        });
    } catch (e) {
        console.warn('Could not load DRISHTI records:', e);
    }
}

function buildLayerToggles() {
    const toggleContainer = document.getElementById('layer-toggles');
    if (!toggleContainer) return;

    const layerDefs = [
        { key: 'watershed_boundary', label: 'Watershed Boundary', color: '#FF7800', defaultOn: true },
        { key: 'ndvi', label: 'NDVI (2026)', color: '#22C55E', defaultOn: false },
        { key: 'ndvi_change', label: 'NDVI Change (2025→2026)', color: '#6366F1', defaultOn: false },
        { key: 'ndwi', label: 'NDWI (2026)', color: '#0EA5E9', defaultOn: false },
        { key: 'water_mask', label: 'Surface Water', color: '#3B82F6', defaultOn: false },
        { key: 'water_change', label: 'Water Change', color: '#8B5CF6', defaultOn: false },
        { key: 'drainage', label: 'Drainage Network (OSM)', color: '#3B82F6', defaultOn: false },
        { key: 'slope', label: 'Terrain Slope', color: '#F59E0B', defaultOn: false },
        { key: 'bhuvan_lulc', label: 'Bhuvan LULC (WMS)', color: '#A855F7', defaultOn: false },
    ];

    toggleContainer.innerHTML = layerDefs.map(def => `
        <label class="layer-toggle">
            <input type="checkbox" data-layer="${def.key}" ${def.defaultOn ? 'checked' : ''}>
            <span class="layer-toggle__dot" style="background: ${def.color}"></span>
            ${def.label}
        </label>
    `).join('');

    toggleContainer.addEventListener('change', (e) => {
        if (e.target.type !== 'checkbox') return;
        const layerKey = e.target.dataset.layer;
        const layer = mapLayers[layerKey];
        if (!layer) return;

        if (e.target.checked) {
            mainMap.addLayer(layer);
        } else {
            mainMap.removeLayer(layer);
        }
        updateMapLegend();
    });

    // Initialize legend state
    updateMapLegend();
}

function updateMapLegend() {
    const legendEl = document.getElementById('map-legend');
    if (!legendEl) return;

    const legends = {
        'ndvi': { title: 'NDVI', min: '-1.0 (Water/Barren)', max: '1.0 (Dense Veg)', gradient: 'linear-gradient(to right, #ffffff, #d2f4d2, #228b22, #006400)' },
        'ndvi_change': { title: 'NDVI Change', min: 'Degraded', max: 'Improved', gradient: 'linear-gradient(to right, #ba1a1a, #ffffff, #10b981)' },
        'ndwi': { title: 'NDWI', min: 'Dry', max: 'Water', gradient: 'linear-gradient(to right, #ffffff, #add8e6, #0000ff)' },
        'water_mask': { title: 'Water Mask', min: 'Non-Water', max: 'Water', gradient: 'linear-gradient(to right, #ffffff, #3B82F6)' },
        'water_change': { title: 'Water Change', min: 'Lost', max: 'Gained', gradient: 'linear-gradient(to right, #ff9999, #ffffff, #9999ff)' },
        'slope': { title: 'Slope', min: 'Flat', max: 'Steep', gradient: 'linear-gradient(to right, #00ff00, #ffff00, #ff0000)' },
    };

    // Find first active layer that has a legend
    const activeToggles = Array.from(document.querySelectorAll('.layer-toggle input[type="checkbox"]:checked'));
    const activeLegendToggle = activeToggles.find(t => legends[t.dataset.layer]);

    if (!activeLegendToggle) {
        legendEl.style.display = 'none';
        return;
    }
    
    const layerKey = activeLegendToggle.dataset.layer;
    const cfg = legends[layerKey];

    legendEl.innerHTML = `
        <div class="map-legend__title">${cfg.title}</div>
        <div class="map-legend__gradient" style="background: ${cfg.gradient}"></div>
        <div class="map-legend__labels">
            <span>${cfg.min}</span>
            <span>${cfg.max}</span>
        </div>
    `;
    legendEl.style.display = 'block';
}


// =============================================================
// Evidence Card Builder (Field views)
// =============================================================
function buildEvidenceCard(data) {
    const statusBadgeClass = {
        'Consistent': 'badge--consistent',
        'Inconclusive': 'badge--inconclusive',
        'Field verification recommended': 'badge--field-verification',
    };

    const severityIcons = {
        'ok': '✓',
        'warning': '!',
        'info': 'i',
    };

    const aiAdvisoryHtml = data.ai_advisory ? `
        <div class="evidence-card__section" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--outline-variant);">
            <div style="font-weight: 600; font-size: 13px; margin-bottom: 6px; color: var(--on-surface);">AI Advisory Report</div>
            <div style="font-size: 12px; color: var(--on-surface-variant); line-height: 1.5;">
                ${data.ai_advisory.replace(/\n/g, '<br>')}
            </div>
        </div>
    ` : '';

    return `
        <div class="evidence-card">
            <div class="evidence-card__header">
                <div class="evidence-card__title">
                    Reported: ${data.reported_intervention || data.intervention_type || 'Unknown'}
                    ${data.ai_predicted_intervention ? `<br><span style="font-size: 12px; color: var(--on-surface-variant); font-weight: 400;">
                        AI Predicted: ${data.ai_predicted_intervention} (Conf: ${data.ai_confidence || '0.0'})
                    </span>` : ''}
                </div>
                <span class="badge ${statusBadgeClass[data.status] || 'badge--inconclusive'}">${data.status}</span>
            </div>
            <div class="evidence-card__body">
                ${(data.evidence || []).map(ev => `
                    <div class="evidence-row">
                        <div class="evidence-row__icon evidence-row__icon--${ev.severity || 'info'}">
                            ${severityIcons[ev.severity] || 'i'}
                        </div>
                        <div class="evidence-row__content">
                            <div class="evidence-row__check">${ev.check}</div>
                            <div class="evidence-row__detail">${ev.detail}</div>
                        </div>
                    </div>
                `).join('')}
                
                ${aiAdvisoryHtml}
            </div>
            <div class="evidence-card__footer">
                <div class="evidence-card__provenance">${data.data_provenance || ''}</div>
            </div>
        </div>
    `;
}


// =============================================================
// Field / DRISHTI View
// =============================================================
let fieldMap = null;
let fieldMarker = null;

function initFieldView() {
    if (!state.fieldMapInitialized) {
        fieldMap = L.map('field-map').setView([15.35, 79.65], 10);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri',
            maxZoom: 18,
        }).addTo(fieldMap);

        // Load basin boundary on field map too
        fetch('/data/downloaded_data/bhuvan/gundlakamma_basin_approx.geojson')
            .then(r => r.json())
            .then(data => {
                L.geoJSON(data, {
                    style: { color: '#FF7800', weight: 2, fillOpacity: 0.05, dashArray: '6 3' }
                }).addTo(fieldMap);
            })
            .catch(() => {});

        // Click map to set coordinates
        fieldMap.on('click', (e) => {
            document.getElementById('field-lat').value = e.latlng.lat.toFixed(5);
            document.getElementById('field-lon').value = e.latlng.lng.toFixed(5);
            updateFieldMarker(e.latlng.lat, e.latlng.lng);
        });

        state.fieldMapInitialized = true;
    } else {
        fieldMap.invalidateSize();
    }

    // Setup form handlers
    setupFieldForm();
}

function updateFieldMarker(lat, lon) {
    if (fieldMarker) fieldMap.removeLayer(fieldMarker);
    fieldMarker = L.marker([lat, lon], {
        icon: L.divIcon({
            className: '',
            html: '<div style="width:16px;height:16px;background:var(--primary);border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
        })
    }).addTo(fieldMap);
    fieldMap.setView([lat, lon], 13);
}

function setupFieldForm() {
    const form = document.getElementById('drishti-form');
    const categorySelect = document.getElementById('field-category');
    const typeSelect = document.getElementById('field-type');
    const photoInput = document.getElementById('field-photo');
    const preview = document.getElementById('photo-preview');

    // Intervention type options by category
    const typeOptions = {
        'Water Harvesting': ['Check Dam', 'Percolation Tank', 'Farm Pond', 'Stop Dam'],
        'Soil Conservation': ['Contour Bunding', 'Trenching', 'Gully Plugs', 'Terracing'],
        'Vegetation/Biomass': ['Afforestation', 'Pasture Development', 'Agro-forestry'],
    };

    categorySelect.addEventListener('change', () => {
        const options = typeOptions[categorySelect.value] || [];
        typeSelect.innerHTML = '<option value="">Select type...</option>' +
            options.map(o => `<option value="${o}">${o}</option>`).join('');
    });

    // Photo preview
    photoInput.addEventListener('change', () => {
        const file = photoInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.innerHTML = `<img src="${e.target.result}" alt="Field photo preview">`;
            };
            reader.readAsDataURL(file);
        }
    });

    // Coordinate inputs update marker
    const latInput = document.getElementById('field-lat');
    const lonInput = document.getElementById('field-lon');
    const updateFromInputs = () => {
        const lat = parseFloat(latInput.value);
        const lon = parseFloat(lonInput.value);
        if (!isNaN(lat) && !isNaN(lon)) {
            updateFieldMarker(lat, lon);
        }
    };
    latInput.addEventListener('change', updateFromInputs);
    lonInput.addEventListener('change', updateFromInputs);

    // Form submission
    form.onsubmit = async (e) => {
        e.preventDefault();

        const submitBtn = document.getElementById('field-submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="material-symbols-outlined">hourglass_empty</span> Uploading & Analyzing...';

        const evidencePanel = document.getElementById('field-evidence');
        evidencePanel.innerHTML = '<div class="loading-spinner">Running field-satellite cross-check...</div>';

        try {
            const formData = new FormData(form);

            const result = await API.postForm('/api/drishti/upload', formData);

            // Prepend AI failure banner if classification failed
            let aiBannerHtml = '';
            if (result.ai_classification_failed) {
                aiBannerHtml = `
                    <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 12px; display:flex; align-items:flex-start; gap: 10px;">
                        <span class="material-symbols-outlined" style="font-size:18px; color:#856404; flex-shrink:0; margin-top:1px;">warning</span>
                        <div>
                            <div style="font-weight: 600; font-size: 13px; color: #856404;">AI Photo Classification Failed</div>
                            <div style="font-size: 12px; color: #664d03; margin-top: 2px;">
                                The uploaded image could not be classified (${result.ai_classification}). 
                                This may indicate the photo is invalid, unreadable, or the AI service is temporarily unavailable.
                                The GIS cross-check below is based on the GPS coordinates only and is still valid.
                                <strong>No AI advisory report has been generated.</strong>
                            </div>
                        </div>
                    </div>
                `;
            }

            // Show evidence
            if (result.crosscheck) {
                const cardHtml = buildEvidenceCard({
                    reported_intervention: formData.get('intervention_type'),
                    ai_predicted_intervention: result.ai_classification_failed ? null : result.ai_classification,
                    ai_confidence: result.ai_classification_failed ? null : result.ai_confidence,
                    status: result.crosscheck.status,
                    evidence: result.crosscheck.evidence,
                    data_provenance: result.crosscheck.data_provenance,
                    ai_advisory: result.ai_classification_failed ? null : result.crosscheck.ai_advisory
                });
                evidencePanel.innerHTML = aiBannerHtml + cardHtml;
            } else {
                evidencePanel.innerHTML = aiBannerHtml;
            }

            // Show success message
            const resultDiv = document.getElementById('field-result');
            resultDiv.innerHTML = `
                <div class="card" style="border-left: 3px solid var(--success);">
                    <p style="color: var(--success-text); font-weight: 600;">
                        <span class="material-symbols-outlined" style="vertical-align:middle;font-size:18px;">check_circle</span>
                        Record saved (ID: ${result.record_id.substring(0, 8)}...)
                    </p>
                    <p style="color: var(--on-surface-variant); margin-top: 4px; font-size: 13px;">
                        Location ${result.location_valid ? 'inside' : 'outside'} watershed.
                        The record will appear on the Monitor map.
                    </p>
                </div>
            `;

            // Invalidate dashboard cache so it refreshes
            state.dashboardData = null;

        } catch (err) {
            evidencePanel.innerHTML = `<p style="color: var(--error);">Error: ${err.message}</p>`;
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span class="material-symbols-outlined">satellite_alt</span> Upload & Run Cross-Check';
        }
    };
}

// =============================================================
// Analysis View
// =============================================================
async function renderAnalysis() {
    const container = document.getElementById('analysis-content');

    if (state.changeData) {
        buildAnalysisUI(container);
        return;
    }

    container.innerHTML = '<div class="loading-spinner">Loading analysis data...</div>';

    try {
        const [change, hotspots, stats] = await Promise.all([
            API.get('/api/change/summary'),
            API.get('/api/change/hotspots?layer=ndvi_change&top_n=15'),
            API.get('/api/watershed/stats'),
        ]);
        state.changeData = change;
        state.hotspots = hotspots.hotspots || [];
        state.watershedStats = stats.stats || {};
        buildAnalysisUI(container);
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Error loading analysis: ${err.message}</p></div>`;
    }
}

function buildAnalysisUI(container) {
    const change = state.changeData?.summary || {};
    const hotspots = state.hotspots || [];
    const stats = state.watershedStats || {};

    const ndviChange = change.ndvi_change || {};
    const ndviCurrent = stats.ndvi_current || {};
    const waterCurrent = stats.water_current || {};

    container.innerHTML = `
        <div class="section-header">
            <div>
                <div class="section-title">Vegetation & Water Change Analysis</div>
                <div class="section-subtitle">Two-date comparison: 2025 vs 2026 (Sentinel-2 derived)</div>
            </div>
            <span class="provenance">
                <span class="material-symbols-outlined" style="font-size:14px;">info</span>
                This is a two-date comparison, NOT a long-term trend.
            </span>
        </div>

        <!-- Summary Stats -->
        <div class="kpi-grid" style="margin-bottom: var(--unit-lg);">
            ${buildKPICard('trending_up', 'green', 'Area Improved', ndviChange.improved_pct != null ? ndviChange.improved_pct.toFixed(1) + '%' : '—', 'NDVI increased > 0.05')}
            ${buildKPICard('remove', 'blue', 'Area Stable', ndviChange.stable_pct != null ? ndviChange.stable_pct.toFixed(1) + '%' : '—', 'NDVI change within ±0.05')}
            ${buildKPICard('trending_down', 'red', 'Area Degraded', ndviChange.degraded_pct != null ? ndviChange.degraded_pct.toFixed(1) + '%' : '—', 'NDVI decreased > 0.05')}
            ${buildKPICard('water_drop', 'blue', 'Water Coverage', waterCurrent.water_area_pct != null ? waterCurrent.water_area_pct.toFixed(1) + '%' : '—', waterCurrent.water_area_ha ? `~${waterCurrent.water_area_ha} ha` : '')}
        </div>

        <!-- Intervention Impact Slider -->
        <div style="margin-bottom: var(--unit-xl);">
            <div class="section-header" style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div>
                    <div class="section-subtitle" style="text-transform:uppercase; font-size:11px; font-weight:700; letter-spacing:0.5px;">Intervention Impact & Spatial Change Detection</div>
                    <div class="section-title">Change Detection: Pre vs Post Intervention</div>
                </div>
                <div style="display:flex; gap: 4px; background:var(--surface-container-high); padding:2px; border-radius:var(--radius-sm);">
                    <button class="btn" style="background:#fff; color:var(--primary); padding:4px 12px; font-size:12px; box-shadow:var(--shadow-sm); border-radius:4px;">Interactive Slider</button>
                    <button class="btn" style="background:transparent; color:var(--on-surface-variant); padding:4px 12px; font-size:12px; border:none;">Side by Side</button>
                </div>
            </div>
            
            <div class="card" style="padding:0; overflow:hidden;">
                <div class="image-slider" id="impact-slider">
                    <!-- Pre Image (Bottom layer) -->
                    <img src="/static/img/pre_map.jpg" alt="Pre Intervention" class="img-before">
                    <div class="slider-label pre">Pre-Intervention Baseline (2021)</div>
                    
                    <!-- Post Image (Top layer, clipped) -->
                    <img src="/static/img/post_map.jpg" alt="Post Intervention" class="img-after" id="impact-slider-after">
                    <div class="slider-label post">Post-Intervention (2024-2025)</div>
                    
                    <!-- Handle & Input -->
                    <div class="image-slider-handle" id="impact-slider-handle"></div>
                    <input type="range" min="0" max="100" value="50" class="image-slider-input" id="impact-slider-input">
                </div>
                
                <div style="display:flex; padding: 16px; background:#fff; border-top:1px solid var(--surface-container-high);">
                    <div style="flex:1; border-right:1px solid var(--surface-container-high); padding-right:16px;">
                        <div style="font-size:12px; color:var(--on-surface-variant);">Vegetation Density</div>
                        <div style="font-weight:600; color:var(--success);">+23.8% increase</div>
                    </div>
                    <div style="flex:1; border-right:1px solid var(--surface-container-high); padding:0 16px;">
                        <div style="font-size:12px; color:var(--on-surface-variant);">Water Retention</div>
                        <div style="font-weight:600; color:var(--info);">+1.4 ha gained</div>
                    </div>
                    <div style="flex:1; border-right:1px solid var(--surface-container-high); padding:0 16px;">
                        <div style="font-size:12px; color:var(--on-surface-variant);">Erosion Hotspots</div>
                        <div style="font-weight:600; color:var(--success);">-64% mitigated</div>
                    </div>
                    <div style="flex:1; padding-left:16px; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:12px; color:var(--on-surface-variant);">Report Status</div>
                            <div style="font-weight:600; color:var(--primary);">Verified</div>
                        </div>
                        <button class="btn btn--primary" style="padding:6px 16px; font-size:13px; border-radius:var(--radius-md);">Export</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="content-grid">
            <!-- Vegetation Statistics -->
            <div>
                <div class="section-header">
                    <div class="section-title">Vegetation Condition (2026)</div>
                </div>
                <div class="card">
                    <div style="margin-bottom: 12px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                            <span style="font: var(--font-body-md); color: var(--on-surface-variant);">High Vegetation (NDVI > 0.4)</span>
                            <span style="font: var(--font-data-mono); font-weight: 600; color: var(--success);">${ndviCurrent.high_veg_pct != null ? ndviCurrent.high_veg_pct.toFixed(1) + '%' : '—'}</span>
                        </div>
                        <div class="stat-bar"><div class="stat-bar__fill stat-bar__fill--green" style="width: ${ndviCurrent.high_veg_pct || 0}%"></div></div>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                            <span style="font: var(--font-body-md); color: var(--on-surface-variant);">Moderate Vegetation (0.2–0.4)</span>
                            <span style="font: var(--font-data-mono); font-weight: 600; color: var(--warning);">${ndviCurrent.moderate_veg_pct != null ? ndviCurrent.moderate_veg_pct.toFixed(1) + '%' : '—'}</span>
                        </div>
                        <div class="stat-bar"><div class="stat-bar__fill stat-bar__fill--orange" style="width: ${ndviCurrent.moderate_veg_pct || 0}%"></div></div>
                    </div>
                    <div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                            <span style="font: var(--font-body-md); color: var(--on-surface-variant);">Low / Bare Soil (NDVI < 0.2)</span>
                            <span style="font: var(--font-data-mono); font-weight: 600; color: var(--error);">${ndviCurrent.low_veg_pct != null ? ndviCurrent.low_veg_pct.toFixed(1) + '%' : '—'}</span>
                        </div>
                        <div class="stat-bar"><div class="stat-bar__fill stat-bar__fill--red" style="width: ${ndviCurrent.low_veg_pct || 0}%"></div></div>
                    </div>
                </div>
            </div>

            <!-- NDVI Change Stats -->
            <div>
                <div class="section-header">
                    <div class="section-title">NDVI Change Statistics</div>
                </div>
                <div class="card">
                    <table class="data-table">
                        <tr><th>Metric</th><th>Value</th></tr>
                        <tr><td>Mean Change</td><td style="font: var(--font-data-mono);">${ndviChange.mean != null ? (ndviChange.mean > 0 ? '+' : '') + ndviChange.mean.toFixed(4) : '—'}</td></tr>
                        <tr><td>Median Change</td><td style="font: var(--font-data-mono);">${ndviChange.median != null ? (ndviChange.median > 0 ? '+' : '') + ndviChange.median.toFixed(4) : '—'}</td></tr>
                        <tr><td>Std. Deviation</td><td style="font: var(--font-data-mono);">${ndviChange.std != null ? ndviChange.std.toFixed(4) : '—'}</td></tr>
                        <tr><td>Max Improvement</td><td style="font: var(--font-data-mono); color: var(--success);">${ndviChange.max != null ? '+' + ndviChange.max.toFixed(4) : '—'}</td></tr>
                        <tr><td>Max Degradation</td><td style="font: var(--font-data-mono); color: var(--error);">${ndviChange.min != null ? ndviChange.min.toFixed(4) : '—'}</td></tr>
                        <tr><td>Valid Pixels</td><td style="font: var(--font-data-mono);">${ndviChange.valid_pixels != null ? ndviChange.valid_pixels.toLocaleString() : '—'}</td></tr>
                    </table>
                </div>
            </div>

            <!-- Change Hotspots -->
            <div class="content-grid--full" style="grid-column: 1 / -1;">
                <div class="section-header">
                    <div class="section-title">Top Change Hotspots (NDVI)</div>
                    <span class="provenance">
                        <span class="material-symbols-outlined" style="font-size:14px;">satellite_alt</span>
                        Pixels with largest absolute NDVI change
                    </span>
                </div>
                <div class="card">
                    <table class="data-table">
                        <tr>
                            <th>#</th>
                            <th>Latitude</th>
                            <th>Longitude</th>
                            <th>NDVI Change</th>
                            <th>Type</th>
                            <th>Action</th>
                        </tr>
                        ${hotspots.map((h, i) => `
                            <tr>
                                <td>${i + 1}</td>
                                <td style="font: var(--font-data-mono);">${h.latitude.toFixed(5)}</td>
                                <td style="font: var(--font-data-mono);">${h.longitude.toFixed(5)}</td>
                                <td style="font: var(--font-data-mono); color: ${h.value > 0 ? 'var(--success)' : 'var(--error)'}; font-weight: 600;">${h.value > 0 ? '+' : ''}${h.value.toFixed(4)}</td>
                                <td><span class="badge ${h.type === 'improvement' ? 'badge--improvement' : 'badge--degradation'}">${h.type}</span></td>
                                <td><button class="btn btn--sm btn--secondary" onclick="navigateTo('map'); setTimeout(() => { if(mainMap) mainMap.setView([${h.latitude}, ${h.longitude}], 14); }, 500);">View</button></td>
                            </tr>
                        `).join('')}
                    </table>
                </div>
            </div>
        </div>

        <div class="disclaimer">
            <div class="disclaimer__title">Interpretation Notes</div>
            <ul class="disclaimer__list">
                <li>Change values are computed as NDVI(2026) − NDVI(2025) within the watershed boundary</li>
                <li>Positive values indicate vegetation increase; negative values indicate decrease</li>
                <li>Pixel resolution is ~111 m; fine-scale features may not be resolved</li>
                <li>Changes may reflect seasonal variation, agricultural cycles, or land use changes</li>
                <li>Hotspots are the pixels with the largest absolute change — they may warrant field verification</li>
            </ul>
        </div>
    `;

    // Initialize image slider
    setTimeout(() => {
        const sliderInput = document.getElementById('impact-slider-input');
        const sliderContainer = document.getElementById('impact-slider');
        if (sliderInput && sliderContainer) {
            sliderInput.addEventListener('input', (e) => {
                sliderContainer.style.setProperty('--exposure', e.target.value + '%');
            });
        }
    }, 100);
}

// =============================================================
// Reports View
// =============================================================
async function renderReports() {
    const container = document.getElementById('reports-content');
    container.innerHTML = '<div class="loading-spinner">Generating evidence report...</div>';

    try {
        const [records, info, stats, change] = await Promise.all([
            API.get('/api/drishti/records'),
            API.get('/api/watershed/info'),
            API.get('/api/watershed/stats'),
            API.get('/api/change/summary'),
        ]);

        const allRecords = records.records || [];
        const disclaimers = info.disclaimers || [];
        const sources = info.data_sources || [];
        const zonalStats = stats.stats || {};
        const changeSummary = change.summary || {};

        const ndviStats = zonalStats.ndvi_current || {};
        const waterStats = zonalStats.water_current || {};
        const ndviChange = changeSummary.ndvi_change || {};

        container.innerHTML = `
            <div class="section-header">
                <div>
                    <div class="section-title">Evidence Summary Report</div>
                    <div class="section-subtitle">${info.name || 'Gundlakamma Watershed'} · ${new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</div>
                </div>
                <button class="btn btn--secondary" onclick="window.print()">
                    <span class="material-symbols-outlined" style="font-size:16px;">print</span>
                    Print Report
                </button>
            </div>

            <!-- Executive Summary -->
            <div class="card" style="margin-bottom: var(--unit-lg);">
                <h3 style="font: var(--font-headline-sm); margin-bottom: var(--unit-sm);">Executive Summary</h3>
                <p style="font: var(--font-body-lg); color: var(--on-surface); margin-bottom: var(--unit-sm);">
                    The ${info.name || 'Gundlakamma Watershed'} in ${info.district || 'Prakasam'} district, ${info.state || 'Andhra Pradesh'}
                    covers approximately ${info.approx_area_km2 || '—'} km². Based on Sentinel-2 satellite imagery analysis:
                </p>
                <ul style="font: var(--font-body-md); color: var(--on-surface); padding-left: 20px; line-height: 1.8;">
                    <li>Mean vegetation index (NDVI) in 2026: <strong>${ndviStats.mean != null ? ndviStats.mean.toFixed(3) : '—'}</strong></li>
                    <li>Surface water coverage: <strong>${waterStats.water_area_pct != null ? waterStats.water_area_pct.toFixed(1) : '—'}%</strong> (~${waterStats.water_area_ha || '—'} ha)</li>
                    <li>Vegetation improvement (2025→2026): <strong>${ndviChange.improved_pct != null ? ndviChange.improved_pct.toFixed(1) : '—'}%</strong> of watershed area</li>
                    <li>Vegetation degradation (2025→2026): <strong>${ndviChange.degraded_pct != null ? ndviChange.degraded_pct.toFixed(1) : '—'}%</strong> of watershed area</li>
                    <li>Total field observations (DRISHTI mock): <strong>${allRecords.length}</strong></li>
                </ul>
            </div>

            <div class="content-grid">
                <!-- Field Records Summary -->
                <div>
                    <div class="section-header">
                        <div class="section-title">Field Observations</div>
                    </div>
                    <div class="card">
                        <table class="data-table">
                            <tr><th>Type</th><th>Stage</th><th>Location</th><th>Date</th></tr>
                            ${allRecords.slice(0, 20).map(r => `
                                <tr>
                                    <td>${r.intervention_type}</td>
                                    <td><span class="badge badge--mock">${r.intervention_stage}</span></td>
                                    <td style="font: var(--font-data-mono); font-size: 12px;">${r.latitude.toFixed(4)}°N, ${r.longitude.toFixed(4)}°E</td>
                                    <td style="font-size: 12px;">${r.timestamp ? new Date(r.timestamp).toLocaleDateString('en-IN', {day:'numeric',month:'short'}) : '—'}</td>
                                </tr>
                            `).join('')}
                        </table>
                        ${allRecords.length > 20 ? `<p style="color:var(--on-surface-variant);margin-top:8px;font-size:12px;">Showing 20 of ${allRecords.length} records.</p>` : ''}
                    </div>
                </div>

                <!-- Data Sources -->
                <div>
                    <div class="section-header">
                        <div class="section-title">Data Sources</div>
                    </div>
                    <div class="card">
                        <table class="data-table">
                            <tr><th>Source</th><th>Provider</th><th>Date</th><th>Resolution</th></tr>
                            ${sources.map(s => `
                                <tr>
                                    <td>${s.name}</td>
                                    <td>${s.provider}</td>
                                    <td>${s.date}</td>
                                    <td style="font: var(--font-data-mono);">${s.resolution}</td>
                                </tr>
                            `).join('')}
                        </table>
                    </div>
                </div>
            </div>

            <!-- Disclaimers -->
            <div class="disclaimer">
                <div class="disclaimer__title">Important Disclaimers</div>
                <ul class="disclaimer__list">
                    ${disclaimers.map(d => `<li>${d}</li>`).join('')}
                </ul>
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Error generating report: ${err.message}</p></div>`;
    }
}

// =============================================================
// Initialize Application
// =============================================================
document.addEventListener('DOMContentLoaded', () => {
    initRouter();
});
