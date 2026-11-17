class Main {
    static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof java.util.Optional) return json(((java.util.Optional<?>)value).orElse(null));
        if (value instanceof String || value instanceof Character) {
            String s=value.toString(); StringBuilder out=new StringBuilder("\"");
            for (int i=0;i<s.length();i++) {
                char c=s.charAt(i);
                if(c=='"' || c=='\\') out.append('\\').append(c);
                else if(c<32) out.append(String.format("\\u%04x",(int)c));
                else out.append(c);
            }
            return out.append('"').toString();
        }
        if (value instanceof Number || value instanceof Boolean) return value.toString();
        java.util.List<String> items=new java.util.ArrayList<>();
        if (value instanceof java.util.Map) {
            for (java.util.Map.Entry<?,?> e: ((java.util.Map<?,?>)value).entrySet()) items.add(json(e.getKey().toString())+":"+json(e.getValue()));
            return "{"+String.join(",",items)+"}";
        }
        if (value instanceof Iterable) {
            for(Object item:(Iterable<?>)value) items.add(json(item));
            return "["+String.join(",",items)+"]";
        }
        throw new IllegalArgumentException("unsupported output type");
    }
    static void write(Object value) throws Exception {
        java.nio.file.Files.writeString(java.nio.file.Path.of("/results/ct-result.json"), json(value));
    }
    public static void main(String[] args) throws Exception {
        Solution solution=new Solution();
        switch(Integer.parseInt(args[0])) { /* CALLS */ default: throw new IllegalArgumentException("input index"); }
    }
}
