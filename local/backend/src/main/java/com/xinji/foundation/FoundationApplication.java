package com.xinji.foundation;

import com.xinji.foundation.config.XinjiProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@EnableConfigurationProperties(XinjiProperties.class)
public class FoundationApplication {
    public static void main(String[] args) {
        SpringApplication.run(FoundationApplication.class, args);
    }
}
