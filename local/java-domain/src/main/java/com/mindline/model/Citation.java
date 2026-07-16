package com.mindline.model;

/**
 * RAG知识引用。
 */
public class Citation {

    private String docId;
    private String title;
    private String snippet;

    public Citation() {}

    public Citation(String docId, String title, String snippet) {
        this.docId = docId;
        this.title = title;
        this.snippet = snippet;
    }

    public String getDocId() { return docId; }
    public void setDocId(String docId) { this.docId = docId; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getSnippet() { return snippet; }
    public void setSnippet(String snippet) { this.snippet = snippet; }
}
