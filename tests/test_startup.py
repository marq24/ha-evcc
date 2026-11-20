"""Regression tests for evcc startup readiness and Home Assistant retries."""

from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.evcc_intg import EvccDataUpdateCoordinator
from custom_components.evcc_intg.const import CONFIG_VERSION, DOMAIN, PLATFORMS
from custom_components.evcc_intg.pyevcc_ha import EvccApiBridge

HOST = "http://evcc.test:7070"
JSON_HEADERS = {"Content-Type": "application/json"}
READY_STATE = {
    "version": "0.319.1",
    "apiReady": True,
    "startupCompleted": True,
    "setupRequired": False,
    "loadpoints": [{"title": "Garage", "vehicleName": "test_vehicle"}],
    "vehicles": {"test_vehicle": {"title": "Test vehicle", "capacity": 60}},
}
FATAL_ERROR = [{"class": "mqtt", "error": "MQTT connection failed"}]
FAILED_STATE = {
    "version": "0.319.1",
    "apiReady": True,
    "startupCompleted": True,
    "setupRequired": True,
    "fatal": FATAL_ERROR,
    "loadpoints": [],
}


@pytest.fixture
def hass_config_dir(hass_tmp_config_dir):
    """Keep all Home Assistant storage in the test's temporary directory."""
    return hass_tmp_config_dir


@pytest.fixture
def config_entry(hass):
    """Create an existing integration entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="evcc",
        version=CONFIG_VERSION,
        data={CONF_HOST: HOST},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_mocks(hass, aioclient_mock):
    """Exercise real setup and discovery without starting entity platforms or WS."""
    aioclient_mock.get(f"{HOST}/api/sessions", json=[], headers=JSON_HEADERS)
    with (
        patch.object(hass.config_entries, "async_forward_entry_setups") as platforms,
        patch.object(EvccDataUpdateCoordinator, "start_watchdog") as watchdog,
    ):
        await hass.async_start()
        yield platforms, watchdog


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"fatal": FATAL_ERROR}, id="fatal"),
        pytest.param({"setupRequired": True}, id="setup-required"),
        pytest.param({"apiReady": False}, id="api-incomplete"),
        pytest.param(
            {"fatal": FATAL_ERROR, "setupRequired": True, "loadpoints": [], "vehicles": {}},
            id="failed-site",
        ),
        pytest.param({"startupCompleted": False}, id="startup-incomplete"),
    ],
)
async def test_unready_state_schedules_setup_retry(
    hass, aioclient_mock, config_entry, setup_mocks, overrides
):
    """An HTTP 200 response must not hide an evcc initialization failure."""
    aioclient_mock.get(f"{HOST}/api/state", json=READY_STATE | overrides, headers=JSON_HEADERS)
    platforms, watchdog = setup_mocks

    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert config_entry.entry_id not in hass.data[DOMAIN]
    platforms.assert_not_called()
    watchdog.assert_not_awaited()


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"fatal": FATAL_ERROR}, id="fatal"),
        pytest.param({"setupRequired": True}, id="setup-required"),
        pytest.param({"apiReady": False}, id="api-incomplete"),
        pytest.param({"startupCompleted": False}, id="startup-incomplete"),
    ],
)
@pytest.mark.parametrize("reread_config", [False, True], ids=["refresh", "config-reread"])
async def test_discovery_rechecks_the_actual_startup_snapshot(
    hass, aioclient_mock, config_entry, setup_mocks, overrides, reread_config
):
    """evcc can become unready after passing the initial availability check."""
    aioclient_mock.get(f"{HOST}/api/state", json=READY_STATE, headers=JSON_HEADERS)
    failed_state = READY_STATE | overrides
    snapshots = [failed_state]
    if reread_config:
        incomplete_state = deepcopy(READY_STATE)
        del incomplete_state["vehicles"]
        snapshots.insert(0, incomplete_state)
    platforms, watchdog = setup_mocks

    with patch.object(EvccApiBridge, "read_state_data", side_effect=snapshots) as read_state:
        assert not await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert read_state.await_count == len(snapshots)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert config_entry.entry_id not in hass.data[DOMAIN]
    platforms.assert_not_called()
    watchdog.assert_not_awaited()


@pytest.mark.parametrize("fatal", [None, []], ids=["null-fatal", "empty-fatal"])
async def test_ready_state_allows_empty_device_lists(
    hass, aioclient_mock, config_entry, setup_mocks, fatal
):
    """Empty vehicles/loadpoints and an empty fatal field are valid."""
    aioclient_mock.get(
        f"{HOST}/api/state",
        json=READY_STATE | {"fatal": fatal, "vehicles": {}, "loadpoints": []},
        headers=JSON_HEADERS,
    )
    platforms, watchdog = setup_mocks

    assert await hass.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator._vehicle == {}
    assert coordinator._loadpoint == {}
    platforms.assert_awaited_once_with(config_entry, PLATFORMS)
    watchdog.assert_awaited_once()


@pytest.mark.parametrize("version", ["0.210.0", "0.319.1"])
async def test_missing_optional_status_flags_are_compatible(
    hass, aioclient_mock, config_entry, setup_mocks, version
):
    """Older responses need not contain the new failure indicators."""
    state = deepcopy(READY_STATE)
    state["version"] = version
    del state["setupRequired"]
    del state["apiReady"]
    if version == "0.210.0":
        del state["startupCompleted"]
    aioclient_mock.get(f"{HOST}/api/state", json=state, headers=JSON_HEADERS)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator._loadpoint["1"]["name"] == "Garage"
    assert coordinator._vehicle["test_vehicle"]["name"] == "Test vehicle"


async def test_home_assistant_retry_discovers_devices_after_recovery(
    hass, aioclient_mock, config_entry, setup_mocks
):
    """The scheduled HA retry creates devices once evcc has recovered."""
    aioclient_mock.get(
        f"{HOST}/api/state",
        json=FAILED_STATE,
        headers=JSON_HEADERS,
    )
    platforms, watchdog = setup_mocks
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{HOST}/api/state", json=READY_STATE, headers=JSON_HEADERS)
    aioclient_mock.get(f"{HOST}/api/sessions", json=[], headers=JSON_HEADERS)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=30))
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator._loadpoint["1"]["name"] == "Garage"
    assert coordinator._vehicle["test_vehicle"]["name"] == "Test vehicle"
    platforms.assert_awaited_once_with(config_entry, PLATFORMS)
    watchdog.assert_awaited_once()
