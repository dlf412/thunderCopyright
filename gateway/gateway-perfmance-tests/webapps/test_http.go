package main

import (
	"log"
	"fmt"
	"flag"
	"runtime"
	"net/http"
	"regexp"
)

var (
	port_flag = flag.Int("port", 9001, "Bind port")
	port int
	size_flag = flag.Int("size", 4, "GOMAXPROCS size")
	size int
)

func init() {
	flag.Parse()
	port = *port_flag
	size = *size_flag
	
	runtime.GOMAXPROCS(size)
}

type Handler struct {
	*regexp.Regexp
}

func (h *Handler) ServeHTTP(wr http.ResponseWriter, req *http.Request) {
	match := h.FindStringSubmatch(req.URL.Path)
	if req.Method != "GET" || match == nil {
		http.Error(wr, "Not found", 404)
		return
	}
	s := match[1]
	fmt.Fprintf(wr, "%s\n", s)
}

func main() {
	h := Handler{regexp.MustCompile("^/([^/]+)$")}
	addr := fmt.Sprintf(":%d", port)
	log.Println("Listening on >> ", addr)
	// http.ListenAndServeTLS(addr, "cert.pem", "key.pem", &h)
	http.ListenAndServe(addr, &h)
}
