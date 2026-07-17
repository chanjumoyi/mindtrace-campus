package com.xinji.foundation.config;

import java.net.http.HttpClient;
import java.time.Duration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class AgentClientConfig {
    @Bean
    RestClient agentRestClient(XinjiProperties properties) {
        Duration timeout = Duration.ofMillis(properties.getAgent().getTimeoutMs());
        HttpClient httpClient = HttpClient.newBuilder().connectTimeout(timeout).build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
        factory.setReadTimeout(timeout);
        return RestClient.builder()
                .baseUrl(properties.getAgent().getBaseUrl())
                .requestFactory(factory)
                .build();
    }
}
