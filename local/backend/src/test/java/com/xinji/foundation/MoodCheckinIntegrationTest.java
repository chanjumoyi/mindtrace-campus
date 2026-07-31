package com.xinji.foundation;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

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
class MoodCheckinIntegrationTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;

    @Test
    void studentCanCreateAndReadOwnMoodTrend() throws Exception {
        String token = login("student_demo", "demo123");
        String body = mvc.perform(post("/api/v1/mood-checkins")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"mood":4,"stress":2,"sleepHours":7.5,
                                 "tags":["学习","运动"]}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.mood").value(4))
                .andExpect(jsonPath("$.data.tags", contains("学习", "运动")))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        String ownerUserId = mapper.readTree(body).path("data").path("ownerUserId").asText();

        mvc.perform(get("/api/v1/mood-checkins")
                        .param("days", "14")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].ownerUserId").value(ownerUserId))
                .andExpect(jsonPath("$.data[0].sleepHours").value(7.5));

        String counselor = login("counselor_demo", "demo123");
        mvc.perform(get("/api/v1/mood-checkins")
                        .param("ownerUserId", ownerUserId)
                        .header("Authorization", "Bearer " + counselor))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].ownerUserId").value(ownerUserId));
    }

    @Test
    void invalidMoodScoreAndCounselorWriteAreRejected() throws Exception {
        String student = login("student_demo", "demo123");
        mvc.perform(post("/api/v1/mood-checkins")
                        .header("Authorization", "Bearer " + student)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"mood\":6,\"stress\":2,\"sleepHours\":7}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_ARGUMENT"));

        String counselor = login("counselor_demo", "demo123");
        mvc.perform(post("/api/v1/mood-checkins")
                        .header("Authorization", "Bearer " + counselor)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"mood\":3,\"stress\":3,\"sleepHours\":7}"))
                .andExpect(status().isForbidden());
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
