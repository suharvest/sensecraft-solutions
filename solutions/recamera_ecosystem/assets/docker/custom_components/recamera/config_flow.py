import voluptuous as vol
from homeassistant import config_entries

from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN


class ReCameraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # 这里可以加一段代码测试连接是否成功
            # 如果成功，创建配置条目
            return self.async_create_entry(
                title=f"reCamera ({user_input[CONF_HOST]})",
                data=user_input
            )

        # 定义表单：输入IP和端口
        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
