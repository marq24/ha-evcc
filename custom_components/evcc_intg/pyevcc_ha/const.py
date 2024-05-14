from enum import Enum
from typing import Final

FILTER_SYSTEMS: Final = "oem,sse,typ,var"
FILTER_VERSIONS: Final = "ccrv,fwc,fwv,cards,var"
FILTER_MIN_STATES: Final = "car,modelStatus,err,nrg,tma,trx"
FILTER_IDS_ADDON: Final = ",pakku,ppv,pgrid"
FILTER_TIMES_ADDON: Final = ",fsptws,inva,lbp,lccfc,lccfi,lcctc,lfspt,lmsc,lpsc,rbt"

FILTER_ALL_STATES: Final = "acu,adi,amt,atp,awcp,car,cbl,ccu,ccw,cdi,cus,deltaa,deltap,err,eto,ffb,fhz,fsp,fsptws,inva,lbp,lccfc,lccfi,lcctc,lck,lfspt,lmsc,loa,lpsc,mcpea,mmp,modelStatus,nif,nrg,pakku,pgrid,pha,pnp,ppv,pvopt_averagePAkku,pvopt_averagePGrid,pvopt_averagePPv,pwm,rbc,rbt,rfb,rssi,rst,tlf,tls,tma,tpa,trx,wh,wsms,wst"
FILTER_ALL_CONFIG: Final = "acp,acs,ama,amp,ara,ate,att,awc,awe,awp,bac,cch,cco,cfi,cid,clp,cwc,cwe,dwo,esk,fmt,fna,frc,frm,fst,fup,fzf,hsa,lbr,lmo,loe,lof,log,lop,lot,loty,lse,map,mca,mci,mcpd,mptwt,mpwst,nmo,pgt,po,psh,psm,psmd,sch_satur,sch_sund,sch_week,sdp,sh,spl3,su,sua,sumd,tds,tof,upo,ust,zfo"

FILTER_NOT_USED: Final = "mcc,mcca,mce,mcr,mcs,mcu,men,mlr,mlra,mqcn,mqg,mqss,msb,msp,msr,mtp,ocppai,ocppi"

# found api-keys that are not documented (yet) ?!
FILTER_UNKNOWN_COMON: Final = "aus,ccd,cle,clea,cll,cmmr,cmp,cms,cmse,csa,ct,ctrls,data,di1,die,dii,dll,hai,hla,isgo,la1,la3,lbl,lcs,lopr,lrc,lri,lrr,lwf,ocppao,ocppcm,ocppcs,ocppf,ocppla,ocpplo,ocppti,pdi,pgr,rdbf,rdbfe,rdbs,rdbse,rde,rdef,rdefe,rdes,rdese,rdpl,rdple,rdre,rdree,smd,tcl,tsi,tzt,ufa,ufe,ufm,ufs,wbw,wda,wsl"
FILTER_UNKNOWN_FW56_2_BETA: Final = "bar,gmtr,gsa,mhe,mht,pco,rmaf,rmav,rmif,rmiv,rsa,rsre,rsrr"
FILTER_UNKNOWN_FW56_1: Final = "avgfhz,simo"


class CAR_VALUES(Enum):
    UNKNOWN = 0
    IDLE = 1
    CHARGING = 2
    WAIT_FOR_CAR = 3
    COMPLETE = 4
    ERROR = 5


TRANSLATIONS: Final = {
    "de": {
        "car": {
            0: "Unbekannt/Fehler",
            1: "Inaktiv/Frei",
            2: "Laden",
            3: "Warte auf Fahrzeug",
            4: "Abgeschlossen",
            5: "Fehler",
        },
        "cus": {
            0: "Unbekannt",
            1: "Entriegelt",
            2: "Entriegelung fehlgeschlagen",
            3: "Verriegelt",
            4: "Verriegelung fehlgeschlagen",
            5: "Ver/Entriegelung Stromausfall",
        },
        "err": {
            0: "-keiner-",
            1: "Fi-AC Fehler",
            2: "Fi-DC Fehler",
            3: "Phasen Fehler",
            4: "Überspannung",
            5: "Überstrom",
            6: "Diode",
            7: "Pp ungültig",
            8: "Keine Masse",
            9: "Schutz klemmt",
            10: "Schutz fehlt",
            11: "Fi unbekannt",
            12: "Unbekannt",
            13: "Überhitzt",
            14: "Keine Kommunikation",
            15: "Verriegelung klemmt (offen)",
            16: "Entriegelung klemmt (gesperrt)",
            17: "?unbekannt?",
            18: "?unbekannt?",
            19: "?unbekannt?",
            20: "Reserviert20",
            21: "Reserviert21",
            22: "Reserviert22",
            23: "Reserviert23",
            24: "Reserviert24",
        },

        # LOADING-Strings...
        # Laden mit internen Fehler

        # NOT-LOADING-Strings
        # Nicht laden im aWATTar Modus
        # Nicht laden im geplanter Ladevorgang Modus
        # Nicht laden, Ladevorgang auf später verschoben
        # Laden gestoppt durch OCPP Backend
        # Laden gestoppt durch zufällige Verzögerung

        # USED/Mapes--Strings:
        # Laden im Ladetimer Modus
        # Laden im Standard Modus
        # Laden mit günstigen aWATTar Preis
        # Laden mit geplanten Ladevorgang, nicht mehr ausreichend Zeit
        # Laden mit geplanten Ladevorgang, keine Uhrzeit
        # Laden mit geplanten Ladevorgang, Testladung
        # Laden mit geplanten Ladevorgang
        # Laden um das Auto wach zu halten
        # Laden weil Ladepause nicht erlaubt
        # Laden mit PV Überschuss
        # Laden manuell freigegeben
        # Nicht laden, durch Ladetimer gestoppt
        # Nicht laden weil kWh Limit erreicht
        # Nicht laden, manuell gestoppt
        # Nicht laden, warte auf Zugangskontrolle
        # Nicht laden weil Übertemperatur
        # Nicht laden, ausstecken simulieren
        # Nicht laden während der Phasenumschaltung
        # Nicht laden, warte minimale Ladepause ab

        # 'geplanten Ladevorgang' -> Next-Trip Modus
        "modelstatus": {
            0: "Nicht laden, weil 'no charge control data'",
            1: "Nicht laden wegen Überhitzung",
            2: "Nicht laden, warte auf Zugangskontrolle",
            3: "Laden manuell freigegeben",
            4: "Nicht laden, da manuell gestoppt",
            5: "Nicht laden, durch Ladetimer gestoppt",
            6: "Nicht laden weil kWh Limit erreicht",
            7: "Laden mit günstigem Strompreis",
            8: "Laden im Next-Trip Modus, Testladung",
            9: "Laden im Next-Trip Modus, keine Uhrzeit",
            10: "Laden im Next-Trip Modus",
            11: "Laden im Next-Trip Modus, nicht mehr ausreichend Zeit",
            12: "Laden mit PV Überschuss",
            13: "Laden im Standard Modus (go-e Default)",
            14: "Laden im Ladetimer Modus (go-e Scheduler)",
            15: "Laden weil 'fallback (Default)'",
            16: "Nicht laden, weil 'Fallback (go-e günstiger Strompreis)'",
            17: "Nicht laden, weil 'Fallback (günstiger Strompreis)'",
            18: "Nicht laden, weil 'Fallback (Automatic Stop)'",
            19: "Laden um das Auto wach zu halten",
            20: "Laden weil Ladepause nicht erlaubt",
            21: "?unbekannt?",
            22: "Nicht laden, ausstecken simulieren",
            23: "Nicht laden während der Phasenumschaltung",
            24: "Nicht laden, warte minimale Ladepause ab",
            25: "?unbekannt?",
            26: "Nicht laden, wegen Fehler",
            27: "Nicht laden, weil vom Lastmanagement abgelehnt",
            28: "Nicht laden, weil vom OCPP abgelehnt",
            29: "Nicht laden, wegen Reconnect Verzögerung",
            30: "Nicht laden, weil der Adapter es blokiert",
            31: "Nicht laden, wegen der 'Under frequency Control'",
            32: "Nicht laden, wegen 'Unbalanced Load'",
            33: "Nicht laden, wegen Entladung der PV Batterie",
            34: "Nicht laden, wegen 'Grid Monitoring'",
            35: "Nicht laden, wegen 'OCPP Fallback'"
        },
        "ffb": {
            0: "Kein Problem",
            1: "Problem beim Verriegeln",
            2: "Problem beim Entriegeln"
        },
        "frm": {
            0: "Netzbezug bevorzugen",
            1: "Default",
            2: "Netzeinspeisung bevorzugen"
        },
        "lck": {
            0: "Normal",
            1: "Auto entriegeln",
            2: "Immer verriegeln",
            3: "Entriegeln erzwingen"
        },
        "pwm": {
            0: "3-Phasen erzwingen",
            1: "Wenn möglich 1-Phase",
            2: "Wenn möglich 3-Phasen"
        },
        "wsms": {
            0: "keiner",
            1: "scann",
            2: "verbinde",
            3: "verbunden"
        },
        "wst": {
            0: "inaktiv/idle",
            1: "Keine SSID verfügbar",
            2: "Scan abgeschlossen",
            3: "verbunden",
            4: "Verbindung fehlgeschlagen",
            5: "Verbindung verloren",
            6: "getrennt",
            7: "?unbekannt?",
            8: "verbinde",
            9: "trenne",
            10: "Kein Schild/No shield"
        }
    },
    "en": {
        "car": {
            0: "Unknown/Error",
            1: "Idle",
            2: "Charging",
            3: "Wait for car",
            4: "Complete",
            5: "Error",
        },
        "cus": {
            0: "Unknown",
            1: "Unlocked",
            2: "Unlock failed",
            3: "Locked",
            4: "Lock failed",
            5: "Lock/Unlock power outage",
        },
        "err": {
            0: "-none-",
            1: "FI AC fault",
            2: "FI DC fault",
            3: "Phase fault",
            4: "Over voltage",
            5: "Over current",
            6: "Diode",
            7: "PP invalid",
            8: "Ground invalid",
            9: "Contactor stuck",
            10: "Contactor missing",
            11: "FI unknown",
            12: "Unknown",
            13: "Over temperature",
            14: "No communication",
            15: "Lock stuck open",
            16: "Lock stuck locked",
            17: "?unknown?",
            18: "?unknown?",
            19: "?unknown?",
            20: "Reserved20",
            21: "Reserved21",
            22: "Reserved22",
            23: "Reserved23",
            24: "Reserved24"
        },
        # 'automatic stop' -> 'Next-Trip Mode'
        "modelstatus": {
            0: "Not charging because no charge control data",
            1: "Not charging because of over temperature",
            2: "Not charging because access control wait",
            3: "Charging because of forced 'on'",
            4: "Not charging because of forced 'off'",
            5: "Not charging because of scheduler",
            6: "Not charging because of energy limit",
            7: "Charging because Awattar price under threshold",
            8: "Charging because of Next-Trip Mode, test charging",
            9: "Charging because of Next-Trip Mode, not enough time",
            10: "Charging because of Next-Trip Mode",
            11: "Charging because of Next-Trip Mode, no clock",
            12: "Charging because of PV surplus",
            13: "Charging because of fallback (go-e Default)",
            14: "Charging because of fallback (go-e Scheduler)",
            15: "Charging because of fallback (Default)",
            16: "Not charging because of fallback (go-e Awattar)",
            17: "Not charging because of fallback (Awattar)",
            18: "Not charging because of fallback (Automatic Stop)",
            19: "Charging because of car compatibility (Keep Alive)",
            20: "Charging because charge pause not allowed",
            21: "?unknown?",
            22: "Not charging because simulate unplugging",
            23: "Not charging because of phase switch",
            24: "Not charging because of minimum pause duration",
            25: "?unknown?",
            26: "Not charging because of Error",
            27: "Not charging because of Load-Management doesn't want",
            28: "Not charging because of OCPP doesn't want",
            29: "Not charging because of reconnect delay",
            30: "Not charging because of adapter blocking",
            31: "Not charging because of under frequency control",
            32: "Not charging because of unbalanced load",
            33: "Not charging because of discharging PV battery",
            34: "Not charging because of grid monitoring",
            35: "Not charging because of OCPP fallback"
        },
        "ffb": {
            0: "No problem",
            1: "Problem with lock",
            2: "Problem with unlock"
        },
        "frm": {
            0: "Prefer power import from grid",
            1: "Default",
            2: "Prefer power export to grid"
        },
        "lck": {
            0: "Normal",
            1: "Auto unlock",
            2: "Always lock",
            3: "Force unlock"
        },
        "pwm": {
            0: "Force 3-Phases",
            1: "Wish 1-Phase",
            2: "Wish 3-Phases"
        },
        "wsms": {
            0: "None",
            1: "Scanning",
            2: "Connecting",
            3: "Connected"
        },
        "wst": {
            0: "Idle status",
            1: "No SSID available",
            2: "Scan completed",
            3: "Connected",
            4: "Connect failed",
            5: "Connection lost",
            6: "Disconnected",
            7: "?unknown?",
            8: "Connecting",
            9: "Disconnecting",
            10: "No shield"
        }
    }
}
