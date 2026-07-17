package com.xinji.foundation.common;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;

@Component
public class Jsons {
    private final ObjectMapper mapper;
    public Jsons(ObjectMapper mapper) { this.mapper = mapper; }
    public String write(Object value) {
        try { return mapper.writeValueAsString(value); }
        catch (JsonProcessingException e) { throw new IllegalStateException("JSON serialization failed", e); }
    }
    public <T> T read(String value, Class<T> type) {
        try { return mapper.readValue(value, type); }
        catch (JsonProcessingException e) { throw new IllegalStateException("JSON deserialization failed", e); }
    }
}
