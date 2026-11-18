'use strict';
const $ = (selector) => document.querySelector(selector);
let reportData = null;
let busy = false;
let controller;
const el = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};
const append = (parent, ...nodes) => { nodes.filter(Boolean).forEach(node => parent.append(node)); return parent; };
const badge = (text, caution = false) => el('span', text, `badge${caution ? ' caution' : ''}`);
const list = (items) => { const node = el('ul'); items.forEach(item => node.append(el('li', item))); return node; };
const card = (title) => { const node = el('article', undefined, 'report-card'); node.append(el('h3', title)); return node; };
const group = (title, items) => { const node = el('div'); append(node, el('h4', title), list(items)); return node; };
const quote = (evidence) => {
  const node = el('blockquote', evidence.quote, 'quote'); node.append(el('cite', `Website evidence · ${evidence.source_id}`)); return node;
};
function selectTab(name) {
  document.querySelectorAll('[role=tab]').forEach(tab => { const active = tab.dataset.panel === name; tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1; });
  document.querySelectorAll('[role=tabpanel]').forEach(panel => { panel.hidden = panel.id !== `panel-${name}`; });
}
document.querySelectorAll('[role=tab]').forEach((tab, index, tabs) => {
  tab.addEventListener('click', () => selectTab(tab.dataset.panel));
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); selectTab(tabs[next].dataset.panel); tabs[next].focus(); }
  });
});
function renderReport(data, sample = false) {
  reportData = data;
  $('#empty-state').hidden = true; $('#report').hidden = false;
  $('#sample-banner').hidden = !sample;
  $('#report-name').textContent = data.brand.name;
  $('#report-summary').textContent = data.brand.summary;
  const meta = $('#report-metadata'); meta.replaceChildren();
  append(meta, badge(data.brand.category), badge(`${data.sources.length} source pages`), badge(sample ? 'Illustrative fixture' : data.metadata.cached ? `Cached · ${data.metadata.cache_age_seconds}s old` : 'Live analysis'), badge(sample ? 'No LLM call' : `${(data.metadata.elapsed_ms / 1000).toFixed(1)}s`), badge(sample ? 'Not a benchmark' : data.metadata.model_used));
  const analysis = data.analysis;
  const brandPanel = $('#panel-brand'); brandPanel.replaceChildren();
  const overview = card('The business, at a glance');
  append(overview, el('p', analysis.competitor_analysis.brand_overview), group('Products & services', data.brand.products_and_services));
  data.brand.evidence.forEach(item => overview.append(quote(item)));
  brandPanel.append(overview);
  const grid = el('div', undefined, 'grid-2');
  append(grid, append(card('Competitive advantages to build on'), list(analysis.competitor_analysis.strengths)), append(card('Where to go next'), list(analysis.competitor_analysis.opportunities)));
  brandPanel.append(grid);
  brandPanel.append(el('p', analysis.competitor_analysis.limitations, 'note'));
  analysis.competitor_analysis.competitors.forEach(competitor => {
    const node = el('article', undefined, 'report-card');
    append(node, append(el('div', undefined, 'competitor-heading'), el('h3', competitor.name), badge('AI suggestion · verify independently', true)), el('p', competitor.comparison));
    const columns = el('div', undefined, 'grid-2');
    append(columns, group('Potential strengths to research', competitor.potential_strengths), group('Potential gaps to research', competitor.potential_gaps));
    node.append(columns); brandPanel.append(node);
  });
  const searchPanel = $('#panel-search'); searchPanel.replaceChildren();
  const searchCard = card('Five ways the right people could find you');
  searchCard.append(el('p', 'Suggested search language, not measured volume or ranking data.'));
  const table = el('table', undefined, 'query-table');
  const head = el('thead'); const header = el('tr');
  ['Search query', 'Platforms', 'Intent', 'Who & why'].forEach(label => {const th = el('th', label); th.scope = 'col'; header.append(th);});
  head.append(header); table.append(head); const body = el('tbody');
  analysis.target_search_queries.forEach(query => { const row = el('tr'); const platforms = el('td'); query.platforms.forEach(platform => platforms.append(badge(platform))); append(row, el('td', query.query), platforms, el('td', query.intent), append(el('td'), el('strong', query.target_audience), el('p', query.business_relevance))); body.append(row); });
  table.append(body); searchCard.append(append(el('div', undefined, 'table-scroll'), table)); searchPanel.append(searchCard);
  const seoPanel = $('#panel-seo'); seoPanel.replaceChildren(); const seo = analysis.seo_improvements;
  const keywords = card('A focused keyword direction'); append(keywords, badge(`Primary · ${seo.primary_keyword}`));
  [['Secondary keywords', seo.secondary_keywords], ['Long-tail opportunities', seo.long_tail_keywords], ['Business keywords', seo.business_keywords]].forEach(([title, values]) => { const chips = el('div', undefined, 'chips'); values.forEach(value => chips.append(el('span', value, 'keyword'))); append(keywords, el('h4', title), chips); });
  seoPanel.append(keywords);
  const snippets = card('A clearer search result'); append(snippets, el('h4', 'Recommended title'), el('p', seo.recommended_title), el('p', seo.title_rationale), el('h4', 'Recommended meta description'), el('p', seo.meta_description)); seoPanel.append(snippets);
  seoPanel.append(append(card('Priority actions'), list(seo.priority_actions)));
  const observations = card('What the HTML actually shows'); data.seo_observations.forEach(observation => { append(observations, el('h4', `${observation.source_id} · ${observation.check.replaceAll('_', ' ')} — ${observation.observed}`), el('p', observation.recommendation)); }); seoPanel.append(observations);
  seo.supporting_content.forEach(content => { seoPanel.append(append(card(content.title), badge(content.content_type.replaceAll('_', ' ')), el('p', content.rationale))); });
  const servicesPanel = $('#panel-services'); servicesPanel.replaceChildren();
  if (analysis.top_services.length < 5) servicesPanel.append(el('p', 'Only supported offerings are listed. The report does not fill five slots by inventing services.', 'note'));
  analysis.top_services.forEach((service, index) => {const node = card(`${String(index + 1).padStart(2, '0')} · ${service.name}`); append(node, badge(service.basis === 'observed' ? 'Observed in website content' : 'Inferred recommendation', service.basis !== 'observed'), el('p', service.description), group('Who it helps', [service.target_industry, service.target_customer]), el('h4', 'Main benefit'), el('p', service.main_benefit)); service.evidence.forEach(item => node.append(quote(item))); if (service.inference_reason) node.append(el('p', service.inference_reason)); servicesPanel.append(node); });
  const audiencePanel = $('#panel-audience'); audiencePanel.replaceChildren(); const audience = analysis.target_audience;
  const audienceGrid = el('div', undefined, 'grid-2');
  [['Primary audience', audience.primary_audience], ['Secondary audience', audience.secondary_audience], ['Industry segments', audience.industries], ['Business types', audience.business_types], ['Customer profiles', audience.customer_profiles], ['Needs & challenges', audience.customer_needs], ['Potential interests', audience.interests], ['Marketing segments to test', audience.marketing_segments]].forEach(([title, values]) => { audienceGrid.append(append(card(title), list(values))); });
  audiencePanel.append(audienceGrid);
  const geography = card('Geographical focus'); geography.append(el('p', audience.geographical_focus || 'Not established by the captured website content.')); audience.geographical_evidence.forEach(item => geography.append(quote(item))); append(audiencePanel, geography, el('p', audience.inference_notes, 'note'));
  const sources = $('#sources'); sources.replaceChildren(); $('#source-count').textContent = `${data.sources.length} captured pages`;
  const notes = el('ul', undefined, 'source-notes'); data.metadata.warnings.forEach(warning => notes.append(el('li', warning))); sources.append(notes);
  data.sources.forEach(source => {const section = el('article', undefined, 'source-block'); append(section, el('h3', `${source.id} · ${source.title || 'Untitled page'}`)); const link = el('a', source.url); try {const url = new URL(source.url); if (['https:', 'http:'].includes(url.protocol)) {link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';}} catch {} append(section, link, el('pre', source.text)); sources.append(section);});
  selectTab('brand');
}
$('#analysis-form').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return;
  busy = true; $('#analyze-button').disabled = true; $('#sample-button').disabled = true;
  $('#error').hidden = true; $('#status').hidden = false; $('#report').hidden = true;
  $('#status').textContent = 'Reading public website content and preparing your analysis. Free models may take a minute.';
  controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 210000);
  try {
    const headers = {'Content-Type': 'application/json'};
    if ($('#api-key').value) headers['X-API-Key'] = $('#api-key').value;
    const response = await fetch('/link-analysis', {method: 'POST', headers, body: JSON.stringify({url: $('#website-url').value}), signal: controller.signal});
    let data; try { data = await response.json(); } catch { throw new Error('The server did not return JSON. A free Render service may still be waking up; try again shortly.'); }
    if (!response.ok || !data.success) throw new Error(`${data.error?.message || 'Analysis failed.'}${data.error?.request_id ? ` Reference: ${data.error.request_id}` : ''}`);
    renderReport(data); $('#report').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (error) {
    $('#error').textContent = error.name === 'AbortError' ? 'Analysis took too long. The server may still be processing; wait briefly before retrying.' : error.message;
    $('#error').hidden = false; $('#empty-state').hidden = false;
  } finally {clearTimeout(timeout); $('#status').hidden = true; busy = false; $('#analyze-button').disabled = false; $('#sample-button').disabled = false;}
});
$('#sample-button').addEventListener('click', async () => {
  if (busy) return; $('#error').hidden = true;
  try {const response = await fetch('/static/sample-report.json'); if (!response.ok) throw new Error('Illustrative report is unavailable.'); renderReport(await response.json(), true); $('#report').scrollIntoView({behavior: 'smooth', block: 'start'});}
  catch (error) {$('#error').textContent = error.message; $('#error').hidden = false;}
});
$('#download-button').addEventListener('click', () => {
  if (!reportData) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(reportData, null, 2)], {type: 'application/json'}));
  const link = el('a'); link.href = url; link.download = $('#sample-banner').hidden ? 'linklens-analysis.json' : 'linklens-illustrative-fixture.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
