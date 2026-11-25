#!/usr/bin/env python3
import os
import json
import time
import uuid
import random
import string
import threading
import asyncio
import traceback
from datetime import datetime, timezone
from functools import wraps
from flask import (
    Flask, request, jsonify, session, redirect, url_for, render_template_string
)

import m
M_AVAILABLE = True
import Bio
BIO_AVAILABLE = True

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "jnl-glory-secret-xyz-123")

ADMIN_KEY = "%$VX43tZ@v52x"
RESELLERS_FILE = "resellers.json"
GROUPS_FILE = "groups.json"
LOCK = threading.Lock()

GLOBAL_LOCK_TIME = 0.0
COOLDOWN_MINS = 45

GROUP_LIFETIME_SEC = 50 * 60
BIO_FIRST_TWO = "[i]Dm @vaibhavff570 On Tg To Buy Glory Bots[/i]"
BIO_LAST_TWO = "[i]Dm @soldflash On Tg To Buy Glory Bots[/i]"
GUILD_FETCH_UID = "8483201645"
GUILD_FETCH_PASSWORD = "113E6894E78051057BC11CEFB9D9DC6FBBDDDA5624B2D7CC81438A9B7E5ECDF0"

REJOIN_WINDOW_SECS = 3 * 60

_ACTIVE_CTLS = {}


def RegisterCtl(GroupId, Ctl):
    with LOCK:
        _ACTIVE_CTLS[GroupId] = Ctl


def UnregisterCtl(GroupId):
    with LOCK:
        _ACTIVE_CTLS.pop(GroupId, None)


def CheckGlobalLock():
    global GLOBAL_LOCK_TIME
    CurrentTime = time.time()
    Elapsed = CurrentTime - GLOBAL_LOCK_TIME
    Limit = COOLDOWN_MINS * 60
    if Elapsed < Limit:
        Remaining = int(Limit - Elapsed)
        Mins, Secs = divmod(Remaining, 60)
        TimeStr = f"{Mins}m {Secs}s"
        return True, f"An Glory Squad Is Already Running Pls Try Again After {TimeStr}"
    return False, None


def SetGlobalLock():
    global GLOBAL_LOCK_TIME
    GLOBAL_LOCK_TIME = time.time()


def GetSquadWait():
    Remaining = int((GLOBAL_LOCK_TIME + COOLDOWN_MINS * 60) - time.time())
    if Remaining <= 0:
        return ""
    Mins, Secs = divmod(Remaining, 60)
    return f"{Mins}m {Secs}s"


LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JNL Glory</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg: #0d1117;
  --surface: #151b28;
  --border: rgba(136, 149, 187, 0.1);
  --border-focus: rgba(212, 162, 78, 0.35);
  --text: #e1e3ea;
  --secondary: #7c839a;
  --muted: #4c526a;
  --accent: #d4a24e;
  --err: #e06575;
  --heading: 'Space Grotesk', sans-serif;
  --body: 'Inter', sans-serif;
  --code: 'JetBrains Mono', monospace;
}

body {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  font-family: var(--body);
  color: var(--text);
}

.wrap {
  width: 92%;
  max-width: 340px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 36px;
}

.brand-mark {
  width: 14px;
  height: 14px;
  background: var(--accent);
  transform: rotate(45deg);
  border-radius: 2px;
  flex-shrink: 0;
}

.brand-name {
  font-family: var(--heading);
  font-size: 15px;
  font-weight: 500;
  color: var(--secondary);
  letter-spacing: 0.03em;
}

h1 {
  font-family: var(--heading);
  font-size: 22px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 6px;
  letter-spacing: -0.02em;
}

.sub {
  font-size: 14px;
  color: var(--secondary);
  margin-bottom: 28px;
  line-height: 1.5;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 28px;
}

.field-label {
  display: block;
  font-size: 13px;
  color: var(--secondary);
  margin-bottom: 8px;
}

input {
  width: 100%;
  padding: 11px 14px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: var(--code);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

input:focus {
  border-color: var(--border-focus);
}

input::placeholder {
  color: var(--muted);
}

.input-group {
  margin-bottom: 22px;
}

button[type=submit] {
  width: 100%;
  padding: 11px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: var(--bg);
  font-family: var(--heading);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.15s;
  letter-spacing: 0.01em;
}

button[type=submit]:hover {
  opacity: 0.88;
}

.err {
  margin-top: 14px;
  font-size: 13px;
  color: var(--err);
  display: flex;
  align-items: center;
  gap: 8px;
}

.err::before {
  content: '!';
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: 1.5px solid var(--err);
  border-radius: 50%;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}
</style>
</head>
<body>
  <div class="wrap">
    <div class="brand">
      <div class="brand-mark"></div>
      <span class="brand-name">JNL Glory</span>
    </div>
    <h1>Welcome back</h1>
    <p class="sub">Enter your product key to continue</p>
    <form class="card" method="POST">
      <div class="input-group">
        <label class="field-label">Product key</label>
        <input type="password" name="admin_key" placeholder="Enter your key" required autofocus autocomplete="off">
      </div>
      <button type="submit">Continue</button>
      {% if error %}<div class="err">{{ error }}</div>{% endif %}
    </form>
  </div>
</body>
</html>
"""

LOADING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Loading</title>
<style>
  body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0d1117;
  }
  .spinner {
    width: 36px;
    height: 36px;
    border: 2.5px solid rgba(136, 149, 187, 0.12);
    border-top-color: #d4a24e;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
</head>
<body>
  <div class="spinner"></div>
  <script>setTimeout(() => { window.location.href = "{{ next_url }}"; }, 1000);</script>
</body>
</html>
"""

PANEL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JNL Glory</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg: #0d1117;
  --surface: #151b28;
  --raised: #1e2535;
  --border: rgba(136, 149, 187, 0.1);
  --border-subtle: rgba(136, 149, 187, 0.06);
  --text: #e1e3ea;
  --secondary: #8b92a8;
  --muted: #4c526a;
  --accent: #d4a24e;
  --green: #58c98d;
  --blue: #6ea8f7;
  --yellow: #e5c062;
  --red: #e06575;
  --heading: 'Space Grotesk', sans-serif;
  --body: 'Inter', sans-serif;
  --code: 'JetBrains Mono', monospace;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--body);
  min-height: 100vh;
  font-size: 14px;
  overflow-x: hidden;
}

.nav {
  position: sticky;
  top: 0;
  height: 52px;
  background: rgba(13, 17, 23, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 100;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-mark {
  width: 12px;
  height: 12px;
  background: var(--accent);
  transform: rotate(45deg);
  border-radius: 2px;
}

.nav-name {
  font-family: var(--heading);
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  letter-spacing: 0.02em;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
}

.nav-link {
  font-size: 13px;
  font-family: var(--body);
  color: var(--muted);
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 6px;
  text-decoration: none;
  transition: color 0.15s, background 0.15s;
}

.nav-link:hover { color: var(--secondary); }
.nav-link.active {
  color: var(--text);
  background: var(--raised);
}

.nav-link.logout { color: var(--muted); }
.nav-link.logout:hover {
  color: var(--red);
  background: rgba(224, 101, 117, 0.06);
}

.main {
  max-width: 1060px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

.page-header { margin-bottom: 24px; }

.page-title {
  font-family: var(--heading);
  font-size: 18px;
  font-weight: 500;
  color: var(--text);
  letter-spacing: -0.01em;
}

.page-desc {
  font-size: 13px;
  color: var(--muted);
  margin-top: 4px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px;
}

.stat-num {
  font-family: var(--heading);
  font-size: 32px;
  font-weight: 400;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 13px;
  color: var(--muted);
}

.console-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 20px;
}

.console-bar {
  border-bottom: 1px solid var(--border);
  padding: 0 16px;
  height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.console-dot {
  width: 7px;
  height: 7px;
  background: var(--green);
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@media (prefers-reduced-motion: reduce) {
  .console-dot { animation: none; }
}

.console-label {
  font-size: 13px;
  color: var(--secondary);
}

.console-body {
  padding: 14px 16px;
  font-family: var(--code);
  font-size: 12px;
  line-height: 1.8;
  color: var(--secondary);
  height: 200px;
  overflow-y: auto;
  background: #0a0e14;
}

.console-body::-webkit-scrollbar { width: 4px; }
.console-body::-webkit-scrollbar-track { background: transparent; }
.console-body::-webkit-scrollbar-thumb { background: var(--raised); border-radius: 2px; }

.log-time { color: var(--muted); margin-right: 10px; }
.log-info { color: var(--blue); }
.log-ok   { color: var(--green); }
.log-warn { color: var(--yellow); }

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 16px;
}

.panel-title {
  font-family: var(--heading);
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.fg { flex: 1; min-width: 160px; }
.fg.sm { flex: 0 0 100px; }

.fg label {
  display: block;
  font-size: 13px;
  color: var(--secondary);
  margin-bottom: 6px;
}

input[type=text], input[type=number], input[type=password] {
  width: 100%;
  padding: 9px 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: var(--code);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

input[type=text]:focus,
input[type=number]:focus {
  border-color: rgba(212, 162, 78, 0.35);
}

input::placeholder { color: var(--muted); }

.btn-primary {
  padding: 9px 18px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: var(--bg);
  font-family: var(--heading);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s;
  height: 38px;
  letter-spacing: 0.01em;
}

.btn-primary:hover { opacity: 0.88; }

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  flex: 0 0 220px;
}

.search-box input {
  padding-left: 32px;
  font-size: 13px;
}

.search-box svg {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  stroke: var(--muted);
  pointer-events: none;
}

.table-wrap { overflow-x: auto; }

table { width: 100%; border-collapse: collapse; }

thead th {
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
  text-align: left;
  padding: 0 12px 12px;
  border-bottom: 1px solid var(--border);
}

thead th:first-child { padding-left: 16px; }

tbody tr {
  border-bottom: 1px solid var(--border-subtle);
  transition: background 0.1s;
  position: relative;
}

tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: var(--raised); }

tbody tr.active-row { background: var(--raised); }

tbody tr.active-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--accent);
  border-radius: 0 1px 1px 0;
}

tbody td {
  padding: 12px;
  font-size: 13px;
  color: var(--secondary);
  vertical-align: middle;
}

tbody td:first-child { padding-left: 16px; }

.key-token {
  font-family: var(--code);
  font-size: 12px;
  color: var(--text);
  background: var(--raised);
  border: 1px solid var(--border);
  padding: 4px 10px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.copy-btn {
  background: none;
  border: none;
  color: var(--muted);
  cursor: pointer;
  padding: 0;
  line-height: 0;
  transition: color 0.15s;
}

.copy-btn:hover { color: var(--secondary); }

.num-accent {
  font-family: var(--heading);
  font-size: 14px;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

.num-muted {
  font-family: var(--code);
  font-size: 13px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.name-cell {
  font-weight: 500;
  color: var(--text);
}

.action-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  margin-right: 4px;
}

.action-btn:hover {
  color: var(--secondary);
  border-color: rgba(136, 149, 187, 0.2);
}

.action-btn.del:hover {
  color: var(--red);
  border-color: rgba(224, 101, 117, 0.25);
  background: rgba(224, 101, 117, 0.04);
}

.tab-content { display: none; }
.tab-content.active { display: block; }

@media (max-width: 680px) {
  .nav { padding: 0 16px; }
  .main { padding: 24px 16px 40px; }
  .stats-row { grid-template-columns: 1fr; }
  .form-row { flex-direction: column; }
  .btn-primary { width: 100%; }
  .search-box { flex: 0 0 100%; }
  .panel-head { flex-direction: column; align-items: flex-start; }
}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-mark"></div>
    <span class="nav-name">JNL Glory</span>
  </div>
  <div class="nav-links">
    <a class="nav-link active" onclick="showTab('dashboard')">Dashboard</a>
    <a class="nav-link" onclick="showTab('resellers')">Resellers</a>
    <a href="/admin/logout" class="nav-link logout">Logout</a>
  </div>
</nav>

<main class="main">

  <div id="dashboard" class="tab-content active">
    <div class="page-header">
      <div class="page-title">Overview</div>
      <div class="page-desc">Reseller activity and node status</div>
    </div>

    <div class="stats-row">
      <div class="stat">
        <div class="stat-num" id="stat-resellers">0</div>
        <div class="stat-label">Resellers</div>
      </div>
      <div class="stat">
        <div class="stat-num" id="stat-remains">0</div>
        <div class="stat-label">Total credits</div>
      </div>
      <div class="stat">
        <div class="stat-num" id="stat-usage">0</div>
        <div class="stat-label">Total usage</div>
      </div>
    </div>

    <div class="console-wrap">
      <div class="console-bar">
        <div class="console-dot"></div>
        <span class="console-label">Live console</span>
      </div>
      <div class="console-body" id="console_logs"></div>
    </div>
  </div>

  <div id="resellers" class="tab-content">
    <div class="page-header">
      <div class="page-title">Resellers</div>
      <div class="page-desc">Manage keys and credits</div>
    </div>

    <div class="panel">
      <div class="panel-title">New reseller</div>
      <div class="form-row">
        <div class="fg">
          <label>Name</label>
          <input type="text" id="r_name" placeholder="e.g. Vaibhav">
        </div>
        <div class="fg sm">
          <label>Credits</label>
          <input type="number" id="r_remains" value="3" min="1">
        </div>
        <button class="btn-primary" onclick="createReseller()">Create key</button>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <div class="panel-title" style="margin-bottom:0">All resellers</div>
        <div class="search-box">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input type="text" id="search_input" placeholder="Search key or name" onkeyup="filterResellers()">
        </div>
      </div>
      <div class="table-wrap">
        <table id="reseller_table">
          <thead>
            <tr>
              <th>Key</th>
              <th>Name</th>
              <th>Credits</th>
              <th>Usage</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </div>

</main>

<script>
let allResellers = [];

function logToConsole(msg, type) {
  const body = document.getElementById('console_logs');
  const t = new Date().toLocaleTimeString('en-GB', {hour12:false});
  const d = document.createElement('div');
  const cls = type === 'success' ? 'log-ok' : type === 'warn' ? 'log-warn' : 'log-info';
  d.innerHTML = '<span class="log-time">' + t + '</span><span class="' + cls + '">' + msg + '</span>';
  body.appendChild(d);
  body.scrollTop = body.scrollHeight;
}

function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  const idx = id === 'dashboard' ? 0 : 1;
  document.querySelectorAll('.nav-link')[idx].classList.add('active');
}

async function fetchResellers() {
  logToConsole('Loading resellers...', 'info');
  const res = await fetch('/admin/api/resellers');
  const data = await res.json();
  if (data.success) {
    allResellers = data.resellers;
    renderTable(allResellers);
    updateStats(allResellers);
    logToConsole('Loaded ' + allResellers.length + ' resellers', 'success');
  } else {
    logToConsole('Failed to load resellers', 'warn');
  }
}

function renderTable(list) {
  const tbody = document.querySelector('#reseller_table tbody');
  tbody.innerHTML = '';
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:28px;font-size:13px;">No resellers yet</td></tr>';
    return;
  }
  list.forEach(r => {
    const d = new Date(r.created_at).toLocaleDateString('en-GB', {day:'2-digit',month:'short',year:'numeric'});
    tbody.innerHTML += `<tr>
      <td><span class="key-token">${r.key}
        <button class="copy-btn" onclick="copyText('${r.key}')" title="Copy">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        </button>
      </span></td>
      <td class="name-cell">${r.name}</td>
      <td><span class="num-accent">${r.remains}</span></td>
      <td><span class="num-muted">${r.usage || 0}</span></td>
      <td style="font-size:12px;font-family:var(--code);color:var(--muted)">${d}</td>
      <td>
        <button class="action-btn" onclick="editRemains('${r.key}', ${r.remains})">Edit</button>
        <button class="action-btn del" onclick="deleteReseller('${r.key}')">Delete</button>
      </td>
    </tr>`;
  });
}

function updateStats(list) {
  let rem = 0, use = 0;
  list.forEach(r => { rem += r.remains; use += (r.usage || 0); });
  document.getElementById('stat-resellers').textContent = list.length;
  document.getElementById('stat-remains').textContent = rem;
  document.getElementById('stat-usage').textContent = use;
}

function filterResellers() {
  const q = document.getElementById('search_input').value.toLowerCase();
  renderTable(allResellers.filter(r => r.key.toLowerCase().includes(q) || r.name.toLowerCase().includes(q)));
}

async function createReseller() {
  const name = document.getElementById('r_name').value.trim();
  const remains = document.getElementById('r_remains').value;
  if (!name) return alert('Enter a name');
  logToConsole('Creating reseller: ' + name, 'info');
  const res = await fetch('/admin/api/resellers', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({name, remains})
  });
  const data = await res.json();
  if (data.success) {
    logToConsole('Created: ' + name, 'success');
    document.getElementById('r_name').value = '';
    fetchResellers();
  } else {
    logToConsole('Error: ' + data.error, 'warn');
    alert('Error: ' + data.error);
  }
}

async function editRemains(key, cur) {
  const val = prompt('New credits for ' + key + ':', cur);
  if (val === null || val.trim() === '') return;
  const n = parseInt(val);
  if (isNaN(n) || n < 0) return alert('Enter a valid number');
  const res = await fetch('/admin/api/resellers/' + key, {
    method: 'PATCH',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({remains: n})
  });
  const data = await res.json();
  if (data.success) { logToConsole('Updated ' + key, 'success'); fetchResellers(); }
  else { logToConsole('Failed to update ' + key, 'warn'); }
}

async function deleteReseller(key) {
  if (!confirm('Delete ' + key + '?')) return;
  logToConsole('Deleting ' + key, 'warn');
  await fetch('/admin/api/resellers/' + key, {method:'DELETE'});
  logToConsole('Deleted ' + key, 'success');
  fetchResellers();
}

function copyText(t) {
  navigator.clipboard.writeText(t);
  logToConsole('Copied ' + t, 'info');
}

logToConsole('JNL Glory ready', 'info');
fetchResellers();
</script>
</body>
</html>

"""


def _load(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_resellers():
    return _load(RESELLERS_FILE, {"resellers": {}})


def save_resellers(data):
    _save(RESELLERS_FILE, data)


def load_groups():
    return _load(GROUPS_FILE, {"groups": {}})


def save_groups(data):
    _save(GROUPS_FILE, data)


def GenerateResellerKey(Length=13):
    Chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(Chars, k=Length))


def CreateReseller(Name, Remains=3):
    with LOCK:
        Data = load_resellers()
        Key = GenerateResellerKey()
        while Key in Data["resellers"]:
            Key = GenerateResellerKey()
        Data["resellers"][Key] = {
            "key": Key, "name": Name, "remains": int(Remains), "usage": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active_groups": []
        }
        save_resellers(Data)
        return Data["resellers"][Key]


def GetReseller(Key):
    Data = load_resellers()
    return Data["resellers"].get(Key)


def ConsumeResellerCredit(Key):
    with LOCK:
        Data = load_resellers()
        Record = Data["resellers"].get(Key)
        if not Record:
            return None
        if Record.get("remains", 0) <= 0:
            return {"error": "no_remains", "reseller": Record}
        Record["remains"] -= 1
        Record["usage"] = Record.get("usage", 0) + 1
        save_resellers(Data)
        return {"reseller": Record}


def FetchGuildInfo(ClanId, Region):
    if not M_AVAILABLE:
        return "Unknown", str(ClanId), 0, 0
    FetchAccount = {
        "uid": GUILD_FETCH_UID,
        "pass": GUILD_FETCH_PASSWORD,
        "region": Region or "IND",
    }
    Loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(Loop)
        Info = Loop.run_until_complete(m.fetch_full_clan_info(FetchAccount, ClanId))
    except Exception as Ex:
        print(f"[GuildFetch] error: {Ex}")
        Info = None
    finally:
        try:
            Loop.close()
        except Exception:
            pass
    if not Info:
        print(f"[GuildFetch] Empty response for clan {ClanId} ({Region})")
        return "Unknown", str(ClanId), 0, 0
    GuildName = Info.get("clan_name") or "Unknown"
    GuildId = str(Info.get("clan_id") or ClanId)
    StartGlory = Info.get("total_glory", 0) or 0
    MemberCount = len(Info.get("members", {}) or {})
    return GuildName, GuildId, StartGlory, MemberCount


def AdminRequired(Fn):
    @wraps(Fn)
    def Wrapper(*Args, **Kwargs):
        if not session.get("admin"):
            if request.path.startswith("/admin/api"):
                return jsonify({"success": False, "error": "auth_required"}), 401
            return redirect(url_for("ClientsPage"))
        return Fn(*Args, **Kwargs)
    return Wrapper


@app.route("/")
def Root():
    return redirect(url_for("ClientsPage"))


@app.route("/clients", methods=["GET", "POST"])
def ClientsPage():
    Error = None
    if request.method == "POST":
        Key = (request.form.get("admin_key") or "").strip()
        if Key == ADMIN_KEY:
            session["admin"] = True
            return redirect(url_for("LoadingPage"))
        Error = "Invalid product key"
    return render_template_string(LOGIN_HTML, error=Error)


@app.route("/loading")
def LoadingPage():
    if not session.get("admin"):
        return redirect(url_for("ClientsPage"))
    return render_template_string(LOADING_HTML, next_url=url_for("AdminPanel"))


@app.route("/admin")
@AdminRequired
def AdminPanel():
    return render_template_string(PANEL_HTML)


@app.route("/admin/logout")
def AdminLogout():
    session.pop("admin", None)
    return redirect(url_for("ClientsPage"))


@app.route("/admin/api/resellers", methods=["GET", "POST"])
@AdminRequired
def AdminResellers():
    if request.method == "GET":
        Data = load_resellers()
        return jsonify({"success": True, "resellers": list(Data["resellers"].values())})
    else:
        Body = request.get_json() or {}
        Name = Body.get("name")
        Remains = int(Body.get("remains", 3))
        if not Name:
            return jsonify({"success": False, "error": "name_required"}), 400
        return jsonify({"success": True, "reseller": CreateReseller(Name, Remains)})


@app.route("/admin/api/resellers/<Key>", methods=["PATCH"])
@AdminRequired
def AdminEditReseller(Key):
    Body = request.get_json() or {}
    if "remains" not in Body:
        return jsonify({"success": False, "error": "remains_required"}), 400
    with LOCK:
        Data = load_resellers()
        if Key not in Data["resellers"]:
            return jsonify({"success": False, "error": "not_found"}), 404
        Data["resellers"][Key]["remains"] = int(Body["remains"])
        save_resellers(Data)
    return jsonify({"success": True})


@app.route("/admin/api/resellers/<Key>", methods=["DELETE"])
@AdminRequired
def AdminDeleteReseller(Key):
    with LOCK:
        Data = load_resellers()
        if Key in Data["resellers"]:
            del Data["resellers"][Key]
            save_resellers(Data)
    return jsonify({"success": True})


def UpdateGroup(GroupId, Fields):
    with LOCK:
        Data = load_groups()
        if GroupId in Data["groups"]:
            Data["groups"][GroupId].update(Fields)
            save_groups(Data)


def ApplyBiosToAccounts(Accounts, CustomBio=None):
    if not BIO_AVAILABLE:
        print("[Bio] Bio module unavailable, skipping")
        return
    for Index, Account in enumerate(Accounts):
        if CustomBio:
            BioText = CustomBio
        else:
            BioText = BIO_FIRST_TWO if Index < 2 else BIO_LAST_TWO
        Jwt = Account.get("jwt")
        if not Jwt:
            continue
        try:
            Ok, Result = Bio.UpdateAccountBio(Jwt, BioText)
            if Ok:
                print(f"[Bio] {Account.get('name')} -> {BioText}")
            else:
                print(f"[Bio] {Account.get('name')} failed: {Result}")
        except Exception as Ex:
            print(f"[Bio] {Account.get('name')} exception: {Ex}")
        time.sleep(0.6)


def CaptureGuildGlory(Accounts, ClanId, Region):
    if not M_AVAILABLE:
        return {"guild_name": "DevGuild", "total_glory": 1000}
    try:
        Account = Accounts[0]
        Loop = asyncio.new_event_loop()
        asyncio.set_event_loop(Loop)
        Info = Loop.run_until_complete(m.fetch_full_clan_info(Account, ClanId))
        Loop.close()
        if Info:
            return {
                "guild_name": Info.get("clan_name") or "Unknown",
                "total_glory": Info.get("total_glory", 0)
            }
    except Exception as Ex:
        print(f"[Launch] glory fetch err: {Ex}")
    return {"guild_name": "Unknown", "total_glory": 0}


def RunLaunchWorker(GroupId, ResellerKey, ClanId, Region, CustomName=None, CustomBio=None):
    try:
        Accounts = []
        Cfg = m.build_region_cfg(Region)
        Loop = asyncio.new_event_loop()
        asyncio.set_event_loop(Loop)
        print(f"[Launch] Generating 4 accounts (Auto-Retry on Captcha)...")
        Attempts = 0
        while len(Accounts) < 4 and Attempts < 15:
            Attempts += 1
            try:
                Account = Loop.run_until_complete(
                    m.create_one_account(len(Accounts) + 1, 4, Cfg, CustomName or "VaixJNL")
                )
                if Account:
                    Accounts.append(Account)
                    print(f"[Launch] Account {len(Accounts)}/4 generated successfully.")
            except Exception as Ex:
                print(f"[Launch] Account gen attempt {Attempts} failed ({Ex}). Retrying in 3s...")
                time.sleep(3)
        Loop.close()
        if len(Accounts) < 4:
            print(f"[Launch] Failed: could only generate {len(Accounts)} accounts out of 4.")
            UpdateGroup(GroupId, {"status": "failed", "error": "account_gen_failed"})
            return
        with LOCK:
            GroupData = load_groups()
            if GroupId in GroupData["groups"]:
                GroupData["groups"][GroupId]["accounts"] = Accounts
                save_groups(GroupData)
        print("[Launch] Applying bios to accounts...")
        ApplyBiosToAccounts(Accounts, CustomBio)
        print(f"[Launch] Joining clan {ClanId}...")
        Joined = JoinAccountsToClan(Accounts, ClanId, Region)
        if not Joined:
            print("[Launch] Failed to join clan.")
            UpdateGroup(GroupId, {"status": "failed", "error": "clan_join_failed"})
            return
        UpdateGroup(GroupId, {"status": "joined", "game_start_at": time.time() + 60})
        print("[Launch] Accounts joined clan. Waiting 60 seconds before starting...")
        time.sleep(60)
        print(f"[Launch] Fetching fresh guild info for clan {ClanId} ({Region})...")
        GuildName, GuildId, FreshGlory, MemberCount = FetchGuildInfo(ClanId, Region)
        print(f"[Launch] Guild: {GuildName} | Glory: {FreshGlory} | Members: {MemberCount}")
        UpdateGroup(GroupId, {
            "guild_name": GuildName,
            "guild_id": GuildId,
            "initial_glory": FreshGlory,
            "total_glory": FreshGlory,
            "member_count": MemberCount,
        })
        print("[Launch] Guild info updated. Starting game now...")
        StartGameLoop(GroupId, Accounts, Region, ClanId)
    except Exception as Ex:
        traceback.print_exc()
        UpdateGroup(GroupId, {"status": "failed", "error": str(Ex)})


def JoinAccountsToClan(Accounts, ClanId, Region):
    if not M_AVAILABLE:
        return True
    Loop = asyncio.new_event_loop()
    asyncio.set_event_loop(Loop)
    try:
        for Account in Accounts:
            try:
                Ok, Msg = Loop.run_until_complete(m.join_clan_for_account(Account, ClanId))
                time.sleep(0.8)
            except Exception as Ex:
                print(f"[Launch] Join err: {Ex}")
                return False
    finally:
        Loop.close()
    return True


def StartGameLoop(GroupId, Accounts, Region, ClanId):
    if not M_AVAILABLE:
        return
    Loop = asyncio.new_event_loop()
    asyncio.set_event_loop(Loop)
    UpdateGroup(GroupId, {"status": "running"})
    with LOCK:
        GroupData = load_groups()
        Group = GroupData["groups"].get(GroupId, {})
    DeadlineTs = Group.get("expires_at")
    if DeadlineTs:
        print(f"[Launch] Group {GroupId} deadline = {datetime.fromtimestamp(DeadlineTs).strftime('%H:%M:%S')}")
    Ctl = m.ParallelCtl(deadline_ts=DeadlineTs)
    RegisterCtl(GroupId, Ctl)
    try:
        Loop.run_until_complete(
            m.run_parallel_game(
                Accounts, region_hint=Region, clan_id=ClanId,
                use_duo=False, game_mode="CS",
                group_id=GroupId, ctl=Ctl, deadline_ts=DeadlineTs
            )
        )
    except Exception as Ex:
        print(f"[Launch] game loop err: {Ex}")
    finally:
        UnregisterCtl(GroupId)
        Loop.close()
        asyncio.set_event_loop(None)
    UpdateGroup(GroupId, {"status": "finished"})


@app.route("/api/v1/launch", methods=["GET"])
@app.route("/api/v2/launch", methods=["GET"])
def ApiLaunch():
    IsV2 = request.path.startswith("/api/v2")
    Key = request.args.get("key")
    ClanId = request.args.get("clan_id")
    Region = (request.args.get("region") or "").upper()
    CustomName = request.args.get("name") if IsV2 else None
    CustomBio = request.args.get("bio") if IsV2 else None

    if not Key or not ClanId or not Region:
        return jsonify({"success": False, "error": "missing_parameters (key, clan_id, region required)"}), 400

    if IsV2:
        if not CustomName or len(CustomName) > 12:
            return jsonify({"success": False, "error": "v2 requires 'name' param (max 12 chars)"}), 400
        if CustomBio is not None and len(CustomBio) > 200:
            return jsonify({"success": False, "error": "v2 'bio' param too long (max 200 chars)"}), 400

    IsLocked, LockMessage = CheckGlobalLock()
    if IsLocked:
        return jsonify({
            "Started": False,
            "Err": LockMessage
        }), 429

    Consumed = ConsumeResellerCredit(Key)
    if Consumed is None:
        return jsonify({"success": False, "error": "invalid_key"}), 403
    if "error" in Consumed:
        return jsonify({"success": False, "error": "no_remains", "message": "Buy from owner @self_client"}), 402

    print(f"[Launch] Fetching guild info for clan {ClanId} ({Region})...")
    GuildName, GuildId, StartGlory, MemberCount = FetchGuildInfo(ClanId, Region)
    print(f"[Launch] Guild: {GuildName} ({GuildId}) start_glory={StartGlory} members={MemberCount}")

    RandomStr = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    GroupId = f"BlueStacks_{RandomStr}"
    ExpiresAt = time.time() + GROUP_LIFETIME_SEC

    with LOCK:
        GroupData = load_groups()
        GroupData["groups"][GroupId] = {
            "group_id": GroupId, "reseller_key": Key, "clan_id": str(ClanId),
            "region": Region, "status": "starting",
            "initial_glory": StartGlory,
            "guild_name": GuildName,
            "guild_id": GuildId,
            "total_glory": StartGlory,
            "member_count": MemberCount,
            "created_at": time.time(), "expires_at": ExpiresAt,
            "api_version": "v2" if IsV2 else "v1",
            "custom_name": CustomName,
            "custom_bio": CustomBio,
            "game_start_at": None,
        }
        save_groups(GroupData)

    SetGlobalLock()

    threading.Thread(
        target=RunLaunchWorker,
        args=(GroupId, Key, str(ClanId), Region, CustomName, CustomBio),
        daemon=True
    ).start()

    return jsonify({
        "Guild Name": GuildName,
        "Guild Id": GuildId,
        "Starting Glory": StartGlory,
        "Gained Glory": 0,
        "success": True,
        "group_id": GroupId,
        "clan_id": str(ClanId),
        "region": Region,
        "remains": Consumed["reseller"]["remains"],
    })


@app.route("/ReJoin", methods=["GET"])
def ApiReJoin():
    Key = request.args.get("key")
    GroupId = request.args.get("group_id")

    if not Key or not GroupId:
        return jsonify({"success": False, "error": "missing_parameters (key, group_id required)"}), 400

    Record = GetReseller(Key)
    if not Record:
        return jsonify({"success": False, "error": "invalid_key"}), 403

    GroupData = load_groups()
    Group = GroupData["groups"].get(GroupId)
    if not Group:
        return jsonify({"success": False, "error": "group_not_found"}), 404

    if Group.get("reseller_key") != Key:
        return jsonify({"success": False, "error": "key_mismatch"}), 403

    GameStartAt = Group.get("game_start_at")
    if not GameStartAt:
        return jsonify({"success": False, "error": "game_not_started_yet"}), 400

    Now = time.time()
    Elapsed = Now - GameStartAt
    if Elapsed > REJOIN_WINDOW_SECS:
        Mins = int(Elapsed // 60)
        return jsonify({
            "success": False,
            "error": f"ReJoin window expired. Match started {Mins}m ago (limit: 3m)"
        }), 400

    if Group.get("status") in ("expired", "finished", "failed"):
        return jsonify({"success": False, "error": f"Group already {Group.get('status')}"}), 400

    Accounts = Group.get("accounts")
    if not Accounts:
        return jsonify({"success": False, "error": "no_accounts_found"}), 400

    ClanId = Group.get("clan_id")
    Region = Group.get("region")

    print(f"[ReJoin] Triggered for group {GroupId} | clan {ClanId} | {Region}")

    def DoReJoin():
        try:
            print(f"[ReJoin] Sending join requests for group {GroupId}...")
            JoinAccountsToClan(Accounts, ClanId, Region)
            print(f"[ReJoin] Done for group {GroupId}")
        except Exception as Ex:
            print(f"[ReJoin] Error: {Ex}")

    threading.Thread(target=DoReJoin, daemon=True).start()

    return jsonify({
        "success": True,
        "message": "ReJoin triggered. Bots are sending clan join requests.",
        "group_id": GroupId,
        "clan_id": ClanId,
        "region": Region,
    })


@app.route("/IsRunning", methods=["GET"])
@app.route("/isrunning", methods=["GET"])
def IsRunning():
    WaitTime = GetSquadWait()
    if not WaitTime:
        return jsonify({"Status": "Not Running"})
    return jsonify({"Status": f"1 Squad Is Already Running Please Wait {WaitTime}"})


@app.route("/api/v1/remains", methods=["GET"])
def ApiRemains():
    Key = request.args.get("key")
    if not Key:
        return jsonify({"success": False, "error": "missing_key"}), 400
    Record = GetReseller(Key)
    if not Record:
        return jsonify({"success": False, "error": "invalid_key"}), 403
    return jsonify({
        "success": True,
        "name": Record.get("name"),
        "remains": Record.get("remains", 0)
    })


@app.route("/api/v1/status", methods=["GET"])
def ApiStatus():
    GroupId = request.args.get("group_id")
    if not GroupId:
        return jsonify({"success": False, "error": "group_id_required"}), 400
    GroupData = load_groups()
    Group = GroupData["groups"].get(GroupId)
    if not Group:
        return jsonify({"success": False, "error": "group_not_found"}), 404
    Now = time.time()
    if Now >= Group["expires_at"] and Group["status"] not in ("expired", "finished", "failed"):
        Group["status"] = "expired"
        with LOCK:
            save_groups(GroupData)
    CurrentTotal = Group.get("total_glory", 0)
    GuildName = Group.get("guild_name", "Unknown")
    GuildId = Group.get("guild_id", Group.get("clan_id", "Unknown"))
    MemberCount = Group.get("member_count", 0)
    if Group.get("status") in ("running", "joined") and Group.get("accounts"):
        try:
            LiveInfo = CaptureGuildGlory(Group["accounts"], Group["clan_id"], Group["region"])
            if LiveInfo and LiveInfo.get("total_glory") is not None:
                CurrentTotal = LiveInfo["total_glory"]
                GuildName = LiveInfo["guild_name"]
                UpdateGroup(GroupId, {"total_glory": CurrentTotal, "guild_name": GuildName})
        except Exception:
            pass
    Initial = Group.get("initial_glory", 0)
    Gained = max(0, CurrentTotal - Initial)
    Reseller = GetReseller(Group["reseller_key"])
    Remains = Reseller["remains"] if Reseller else 0
    return jsonify({
        "success": True,
        "Guild Name": GuildName,
        "Guild Id": str(GuildId),
        "Starting Glory": Initial,
        "Gained Glory": Gained,
        "guild_name": GuildName,
        "guild_id": str(GuildId),
        "initial_glory": Initial,
        "total_glory": CurrentTotal,
        "gained_glory": Gained,
        "member_count": MemberCount,
        "region": Group.get("region"),
        "remains": Remains,
        "status": Group.get("status")
    })


def ExpiryLoop():
    while True:
        try:
            ExpiredGroups = []
            with LOCK:
                Data = load_groups()
                Now = time.time()
                Changed = False
                for Gid, Group in Data["groups"].items():
                    if Now >= Group.get("expires_at", 0) and Group.get("status") not in ("expired", "finished", "failed"):
                        Group["status"] = "expired"
                        Changed = True
                        ExpiredGroups.append(Gid)
                if Changed:
                    save_groups(Data)
            for Gid in ExpiredGroups:
                Ctl = _ACTIVE_CTLS.get(Gid)
                if Ctl is not None:
                    try:
                        Ctl.cancel(Gid)
                        print(f"[Expiry] Group {Gid} — game cancelled (timeout)")
                    except Exception as Ex:
                        print(f"[Expiry] cancel err for {Gid}: {Ex}")
                else:
                    print(f"[Expiry] Group {Gid} marked expired (no active game)")
        except Exception as Ex:
            print(f"[Expiry] {Ex}")
        time.sleep(60)


threading.Thread(target=ExpiryLoop, daemon=True).start()

if __name__ == "__main__":
    Port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=Port, threaded=True)
