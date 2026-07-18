package com.xinji.foundation.handwriting;

import com.fasterxml.jackson.databind.JsonNode;
import com.xinji.foundation.common.ApiResponse;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.config.XinjiProperties;
import java.time.Duration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@RestController
@RequestMapping("/api/v1/handwriting")
public class HandwritingGatewayController {
    private final RestClient client;

    public HandwritingGatewayController(XinjiProperties properties) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(properties.getHandwriting().getTimeoutMs()));
        factory.setReadTimeout(Duration.ofMillis(properties.getHandwriting().getTimeoutMs()));
        this.client = RestClient.builder()
                .baseUrl(properties.getHandwriting().getBaseUrl())
                .requestFactory(factory)
                .build();
    }

    @PostMapping("/analyze")
    public ApiResponse<JsonNode> analyze(@RequestBody JsonNode request) {
        try {
            JsonNode envelope = client.post()
                    .uri("/api/v1/handwriting/analyze")
                    .body(request)
                    .retrieve()
                    .body(JsonNode.class);
            if (envelope == null || !envelope.path("success").asBoolean(false)) {
                String message = envelope == null ? "笔迹分析服务未返回结果" : envelope.path("message").asText("笔迹分析失败");
                throw new BusinessException(ErrorCode.AGENT_UNAVAILABLE, message);
            }
            return ApiResponse.ok(envelope.path("data"));
        } catch (BusinessException error) {
            throw error;
        } catch (RestClientException error) {
            throw new BusinessException(ErrorCode.AGENT_UNAVAILABLE, "笔迹分析服务暂不可用，请确认本地 8091 服务已启动");
        }
    }
}
