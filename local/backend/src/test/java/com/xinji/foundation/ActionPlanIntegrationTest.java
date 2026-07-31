package com.xinji.foundation;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ActionPlanIntegrationTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;

    @Test
    void studentCanCreateAndCompleteOwnActionPlan() throws Exception {
        String token = login("student_demo", "demo123");
        String body = mvc.perform(post("/api/v1/action-plans")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"title":"稳定作息","items":[
                                  {"title":"睡前十分钟放下手机"},
                                  {"title":"早晨到户外走一走"}
                                ]}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("ACTIVE"))
                .andExpect(jsonPath("$.data.items[*].status", contains("PENDING", "PENDING")))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        JsonNode data = mapper.readTree(body).path("data");
        String planId = data.path("id").asText();
        String firstItemId = data.path("items").get(0).path("id").asText();
        String secondItemId = data.path("items").get(1).path("id").asText();

        update(token, planId, firstItemId, "完成后更容易入睡", "ACTIVE");
        update(token, planId, secondItemId, null, "COMPLETED");

        mvc.perform(get("/api/v1/action-plans")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].id").value(planId))
                .andExpect(jsonPath("$.data[0].status").value("COMPLETED"));

        String counselor = login("counselor_demo", "demo123");
        mvc.perform(get("/api/v1/action-plans")
                        .param("ownerUserId", data.path("ownerUserId").asText())
                        .header("Authorization", "Bearer " + counselor))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].id").value(planId));
        mvc.perform(post("/api/v1/action-plans")
                        .header("Authorization", "Bearer " + counselor)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"代建计划\",\"items\":[{\"title\":\"不应允许\"}]}"))
                .andExpect(status().isForbidden());
    }

    @Test
    void emptyPlanIsRejected() throws Exception {
        String token = login("student_demo", "demo123");
        mvc.perform(post("/api/v1/action-plans")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"空计划\",\"items\":[]}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_ARGUMENT"));
    }

    private void update(String token, String planId, String itemId, String feedback, String expectedPlanStatus)
            throws Exception {
        String payload = mapper.writeValueAsString(java.util.Map.of(
                "status", "DONE", "feedback", feedback == null ? "" : feedback));
        mvc.perform(patch("/api/v1/action-plans/{planId}/items/{itemId}", planId, itemId)
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(payload))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value(expectedPlanStatus));
    }

    private String login(String username, String password) throws Exception {
        String body = mvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(java.util.Map.of(
                                "username", username, "password", password))))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        return mapper.readTree(body).path("data").path("accessToken").asText();
    }
}
