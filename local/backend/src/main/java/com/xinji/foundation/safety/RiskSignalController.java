package com.xinji.foundation.safety;

import com.xinji.foundation.auth.SecurityUtils;
import org.springframework.web.bind.annotation.*;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/risk-signals")
public class RiskSignalController {

    private final RiskSignalRepository repository;

    public RiskSignalController(RiskSignalRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public List<RiskSignalEntity> listMySignals() {
        var actor = SecurityUtils.current();
        return repository.findTop50ByUserIdOrderByCreatedAtDesc(actor.id());
    }

    @PostMapping
    public RiskSignalEntity create(@RequestBody Map<String, String> body) {
        var actor = SecurityUtils.current();
        var entity = new RiskSignalEntity();
        entity.setId(UUID.randomUUID().toString());
        entity.setUserId(body.getOrDefault("userId", actor.id()));
        entity.setLevel(body.getOrDefault("level", "YELLOW"));
        entity.setSource(body.getOrDefault("source", "user_input"));
        entity.setTriggerContent(body.getOrDefault("triggerContent", ""));
        entity.setCreatedAt(OffsetDateTime.now());
        return repository.save(entity);
    }
}
