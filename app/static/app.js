'use strict';
const $ = (selector) => document.querySelector(selector);
let reportData = null;
let reportMode = "live";
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
  const node = el('blockquote', evidence.quote, 'quote'); const citation = el('cite'); const jump = el('button', `View source ${evidence.source_id} →`, 'source-jump');
  jump.type = 'button'; jump.addEventListener('click', () => {
    $('.source-details').open = true;
    document.getElementById(`source-${evidence.source_id}`)?.scrollIntoView({behavior: 'smooth', block: 'center'});
  }); citation.append(jump); node.append(citation); return node;
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
function renderReport(data, mode = "live") {
  reportData = data; reportMode = mode;
  const sample = mode === "illustrative"; const recorded = mode === "recorded";
  $('#empty-state').hidden = true; $('#report').hidden = false;
  $('#sample-banner').hidden = !sample && !recorded;
  $('#sample-banner').textContent = sample
    ? 'ILLUSTRATIVE TEST REPORT · Fictional website data, not a live model response.'
    : recorded ? `RECORDED LIVE REPORT · Generated ${new Date(data.metadata.generated_at).toISOString().replace('T', ' ').slice(0, 19)} UTC. This is a saved real response, not a new analysis.` : '';
  $('#report-name').textContent = data.brand.name;
  $('#report-summary').textContent = data.brand.summary;
  const meta = $('#report-metadata'); meta.replaceChildren();
  append(meta, badge(data.brand.category), badge(`${data.sources.length} pages reviewed`), badge(sample ? 'Illustrative fixture' : recorded ? 'Recorded live result' : data.metadata.cached ? `Cached · ${data.metadata.cache_age_seconds}s old` : 'Live analysis'), badge(sample ? 'No model call' : `${recorded ? 'Original run · ' : ''}${(data.metadata.elapsed_ms / 1000).toFixed(1)} seconds`));
  const analysis = data.analysis;
  const brandPanel = $('#panel-brand'); brandPanel.replaceChildren();
  const overview = card('The business, at a glance');
  append(overview, el('p', analysis.competitor_analysis.brand_overview), group('Products & services', data.brand.products_and_services));
  if (data.brand.evidence.length) overview.append(quote(data.brand.evidence[0]));
  if (data.brand.evidence.length > 1) {
    const more = el('details', undefined, 'more-evidence');
    more.append(el('summary', `Show ${data.brand.evidence.length - 1} more source excerpts`));
    data.brand.evidence.slice(1).forEach(item => more.append(quote(item))); overview.append(more);
  }
  brandPanel.append(overview);
  const grid = el('div', undefined, 'grid-2');
  append(grid, append(card('Competitive advantages to build on'), list(analysis.competitor_analysis.strengths)), append(card('Where to go next'), list(analysis.competitor_analysis.opportunities)));
  brandPanel.append(grid);
  brandPanel.append(el('p', analysis.competitor_analysis.limitations, 'note'));
  analysis.competitor_analysis.competitors.forEach(competitor => {
    const node = el('details', undefined, 'report-card competitor-card');
    const heading = el('summary');
    append(heading, append(el('div', undefined, 'competitor-heading'), el('h3', competitor.name), badge('AI suggestion · verify independently', true)), el('p', competitor.comparison));
    node.append(heading);
    const columns = el('div', undefined, 'grid-2');
    append(columns, group('Potential strengths to research', competitor.potential_strengths), group('Potential gaps to research', competitor.potential_gaps));
    node.append(columns); brandPanel.append(node);
  });
  const searchPanel = $('#panel-search'); searchPanel.replaceChildren();
  const searchCard = card('Five ways the right people could find you');
  searchCard.append(el('p', 'Suggested search language, not measured volume or ranking data.'));
  searchPanel.append(searchCard);
  const searchGrid = el('div', undefined, 'search-grid');
  analysis.target_search_queries.forEach((query, index) => {
    const node = el('article', undefined, 'report-card');
    append(node, append(el('div', undefined, 'search-query-head'), el('span', String(index + 1).padStart(2, '0'), 'query-number'), el('h3', query.query)));
    const platforms = el('div', undefined, 'query-platforms'); query.platforms.forEach(platform => platforms.append(badge(platform)));
    append(node, platforms, el('p', query.intent, 'query-intent'), el('h4', 'For'), el('p', query.target_audience), el('h4', 'Why it fits'), el('p', query.business_relevance));
    searchGrid.append(node);
  });
  searchPanel.append(searchGrid);
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
  analysis.top_services.forEach((service, index) => {const node = card(`${String(index + 1).padStart(2, '0')} · ${service.name}`); append(node, badge(service.basis === 'observed' ? 'Observed in website content' : 'Inferred recommendation', service.basis !== 'observed'), el('p', service.description), group('Who it helps', [service.target_industry, service.target_customer]), el('h4', 'Main benefit'), el('p', service.main_benefit)); service.evidence.forEach(item => node.append(quote(item))); if (service.basis === 'inferred_recommendation' && service.inference_reason) node.append(el('p', service.inference_reason)); servicesPanel.append(node); });
  const audiencePanel = $('#panel-audience'); audiencePanel.replaceChildren(); const audience = analysis.target_audience;
  const audienceGrid = el('div', undefined, 'grid-2');
  [['Primary audience', audience.primary_audience], ['Secondary audience', audience.secondary_audience], ['Industry segments', audience.industries], ['Business types', audience.business_types], ['Customer profiles', audience.customer_profiles], ['Needs & challenges', audience.customer_needs], ['Potential interests', audience.interests], ['Marketing segments to test', audience.marketing_segments]].forEach(([title, values]) => { audienceGrid.append(append(card(title), list(values))); });
  audiencePanel.append(audienceGrid);
  const geography = card('Geographical focus'); geography.append(el('p', audience.geographical_focus || 'Not established by the captured website content.')); audience.geographical_evidence.forEach(item => geography.append(quote(item))); append(audiencePanel, geography, el('p', audience.inference_notes, 'note'));
  const sources = $('#sources'); sources.replaceChildren(); $('#source-count').textContent = `${data.sources.length} captured pages`;
  const method = el('p', `Model: ${data.metadata.model_used} · Generated: ${data.metadata.generated_at} · Original usage: ${data.metadata.usage.input_tokens ?? 'unavailable'} input / ${data.metadata.usage.output_tokens ?? 'unavailable'} output tokens.`, 'method-note'); sources.append(method);
  const notes = el('ul', undefined, 'source-notes'); data.metadata.warnings.forEach(warning => notes.append(el('li', warning))); sources.append(notes);
  data.sources.forEach(source => {const section = el('article', undefined, 'source-block'); section.id = `source-${source.id}`; append(section, el('h3', `${source.id} · ${source.title || 'Untitled page'}`)); const link = el('a', source.url); try {const url = new URL(source.url); if (['https:', 'http:'].includes(url.protocol)) {link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';}} catch {} append(section, link, el('pre', source.text)); sources.append(section);});
  selectTab('brand');
  $('#report-name').tabIndex = -1; $('#report-name').focus({preventScroll: true});
}
function setBusy(value) {
  busy = value;
  ['#analyze-button', '#sample-button', '#recorded-button', '#try-button'].forEach(selector => { $(selector).disabled = value; });
  $('#analyze-label').textContent = value ? 'Analyzing…' : 'Analyze';
  $('#website-url').readOnly = value;
}
const friendlyErrors = {
  llm_rate_limited: 'The free AI models are busy right now. Try again in a minute, or explore the recorded report.',
  llm_unavailable: 'The AI service is temporarily unavailable. You can still explore the recorded report below.',
  llm_timeout: 'The analysis took longer than expected. Please try again shortly, or open the recorded report.',
  unauthorized: 'This deployment is private. Open Developer tools below and enter the deployment access key.',
  llm_not_configured: 'Live analysis is not configured on this deployment yet. You can explore the recorded report.',
  invalid_request: 'Please enter a public website address, such as basecamp.com.',
  insufficient_content: 'There is not enough readable content on this page. Try the company homepage or another public page.',
  website_restricted: 'This website blocks automated reading. Try another public website.',
  rate_limited: 'You have made several requests recently. Please wait a minute before trying again.',
  server_busy: 'Two reports are already being prepared. Please try again shortly.',
  invalid_model_output: 'The AI response did not pass our quality checks. Please try again, or view the recorded report.'
};
$('#analysis-form').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return;
  let url = $('#website-url').value.trim();
  if (!/^[a-z][a-z0-9+.-]*:/i.test(url)) url = 'https://' + url;
  try {
    const parsed = new URL(url);
    if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error();
    $('#website-url').value = url;
  } catch {
    $('#error').textContent = 'Please enter a website address, such as https://example.com.';
    $('#error').hidden = false; return;
  }
  setBusy(true);
  $('#error').hidden = true; $('#status').hidden = false; $('#report').hidden = true;
  $('#status-message').textContent = `Taking a closer look at ${new URL(url).hostname}…`;
  controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 210000);
  try {
    const headers = {'Content-Type': 'application/json'};
    if ($('#api-key').value) headers['X-API-Key'] = $('#api-key').value;
    const response = await fetch('/link-analysis', {method: 'POST', headers, body: JSON.stringify({url}), signal: controller.signal});
    let data; try { data = await response.json(); } catch { throw new Error('The server may still be waking up. Please try again shortly.'); }
    if (!response.ok || !data.success) {
      const error = new Error(friendlyErrors[data.error?.code] || data.error?.message || 'We could not complete the analysis. Please try again.');
      error.reference = data.error?.request_id; throw error;
    }
    renderReport(data); $('#report').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (error) {
    $('#error').replaceChildren(el('span', error.name === 'AbortError' ? 'Request cancelled or timed out. The server may still finish the report; please wait briefly before retrying.' : error.message));
    if (error.reference) $('#error').append(el('small', ` Reference: ${error.reference}`));
    $('#error').hidden = false; $('#empty-state').hidden = false;
  } finally {clearTimeout(timeout); $('#status').hidden = true; setBusy(false);}
});
$('#cancel-button').addEventListener('click', () => controller?.abort());
$('#try-button').addEventListener('click', () => {if (busy) return; $('#website-url').value = 'https://basecamp.com'; $('#analysis-form').requestSubmit();});
$('#new-analysis-button').addEventListener('click', () => {$('#analysis-form').scrollIntoView({behavior: 'smooth', block: 'center'}); $('#website-url').focus({preventScroll: true}); $('#website-url').select();});
async function loadSavedReport(path, mode) {
  if (busy) return; $('#error').hidden = true;
  try {
    const response = await fetch(path);
    if (!response.ok) throw new Error('This saved report is not available yet. Please try a live analysis instead.');
    renderReport(await response.json(), mode); $('#report').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (error) {$('#error').textContent = error.message; $('#error').hidden = false;}
}
$('#sample-button').addEventListener('click', () => loadSavedReport('/static/sample-report.json', 'illustrative'));
$('#recorded-button').addEventListener('click', () => loadSavedReport('/static/recorded-report.json', 'recorded'));
$('#download-button').addEventListener('click', () => {
  if (!reportData) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(reportData, null, 2)], {type: 'application/json'}));
  const link = el('a'); link.href = url; link.download = `linklens-${reportMode}-report.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
