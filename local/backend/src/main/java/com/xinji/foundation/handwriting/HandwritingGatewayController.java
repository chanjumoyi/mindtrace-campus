package com.xinji.foundation.handwriting;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.xinji.foundation.common.ApiResponse;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.config.XinjiProperties;
import java.time.Duration;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.http.client.BufferingClientHttpRequestFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

@RestController
@RequestMapping("/api/v1/handwriting")
public class HandwritingGatewayController {
    private final RestClient client;
    private final ObjectMapper mapper = new ObjectMapper();

    public HandwritingGatewayController(XinjiProperties properties) {
        Duration timeout = Duration.ofMillis(properties.getHandwriting().getTimeoutMs());
        var inner = new SimpleClientHttpRequestFactory();
        inner.setConnectTimeout(timeout);
        inner.setReadTimeout(timeout);
        var factory = new BufferingClientHttpRequestFactory(inner);
        this.client = RestClient.builder()
                .baseUrl(properties.getHandwriting().getBaseUrl())
                .requestFactory(factory)
                .build();
    }

    @PostMapping("/analyze")
    public ApiResponse<JsonNode> analyze(@RequestBody JsonNode request) {
        try {
            ResponseEntity<String> raw = client.post()
                    .uri("/api/v1/handwriting/analyze")
                    .body(request)
                    .retrieve()
                    .toEntity(String.class);
            JsonNode envelope = mapper.readTree(raw.getBody());
            if (!raw.getStatusCode().is2xxSuccessful() || !envelope.path("success").asBoolean(false)) {
                String msg = envelope.path("message").asText("笔迹分析失败");
                throw new BusinessException(raw.getStatusCode().is4xxClientError() ? ErrorCode.INVALID_ARGUMENT : ErrorCode.AGENT_UNAVAILABLE, msg);
            }
            return ApiResponse.ok(envelope.path("data"));
        } catch (BusinessException error) {
            throw error;
        } catch (Exception error) {
            throw new BusinessException(ErrorCode.AGENT_UNAVAILABLE, "笔迹分析服务暂不可用: " + error.getMessage());
        }
    }
}
