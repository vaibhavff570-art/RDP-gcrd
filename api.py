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
    Flask, request, jsonify, session, redirect, url_for, render_template
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
    return render_template("login.html", error=Error)


@app.route("/loading")
def LoadingPage():
    if not session.get("admin"):
        return redirect(url_for("ClientsPage"))
    return render_template("loading.html", next_url=url_for("AdminPanel"))


@app.route("/admin")
@AdminRequired
def AdminPanel():
    return render_template("panel.html")


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
