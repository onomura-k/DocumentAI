#!/usr/bin/env python3
"""
Google Cloud Document AI - Document OCRプロセッサ専用スクリプト
座標精度重視でテキスト抽出と画像切り抜きを実行
"""

import json
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import io

try:
    from google.cloud import documentai_v1 as documentai
    from PIL import Image, ImageDraw
except ImportError as e:
    print(f"❌ 必要なライブラリがインストールされていません: {e}")
    print("以下のコマンドでインストールしてください:")
    print("pip install google-cloud-documentai pillow")
    exit(1)


class DocumentOCRProcessor:
    """Document OCRプロセッサによる座標付きテキスト抽出と画像切り抜き"""
    
    def __init__(self):
        # 設定情報
        self.config = {
            "project_id": "gen-lang-client-0849825641",  # 正しいプロジェクトID
            "location": "us",  # Document OCRプロセッサのロケーション
            "ocr_processor_id": "d784f2907961b8a6",  # Document OCRプロセッサ
            "pdf_path": "sample.pdf",
            "output_dir": "extracted_images"
        }
        
        # Document AI v1 クライアント初期化（リージョン別エンドポイント）
        from google.api_core.client_options import ClientOptions
        opts = ClientOptions(api_endpoint=f"{self.config['location']}-documentai.googleapis.com")
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        # 出力ディレクトリ作成
        Path(self.config["output_dir"]).mkdir(exist_ok=True)
        
        # 推定画像エリア検索用キーワード
        self.chair_keywords = [
            'エッグチェア', 'アントチェア', 'スワンチェア', 'セブンチェア',
            'ベルビュー・チェア', 'アリンコチェア'
        ]
        
        # 推定エリアのオフセット設定（ページ全体に対する割合）
        self.area_offset = {
            'top': 0.1,     # 上方向10%
            'bottom': 0.1,  # 下方向10%
            'left': 0.15,   # 左方向15%
            'right': 0.15   # 右方向15%
        }
        
        # 推定画像エリア検索用キーワード
        self.chair_keywords = [
            'エッグチェア', 'アントチェア', 'スワンチェア', 'セブンチェア',
            'ベルビュー・チェア', 'アリンコチェア'
        ]
        
        # 推定エリアのオフセット設定（ページ全体に対する割合）
        self.area_offset = {
            'top': 0.1,     # 上方向10%
            'bottom': 0.1,  # 下方向10%
            'left': 0.15,   # 左方向15%
            'right': 0.15   # 右方向15%
        }
    
    def get_process_options(self):
        """Document OCR用のProcessOptions設定（visual_elements検出強化）"""
        # Document OCRで図表検出を最大化する設定
        return documentai.ProcessOptions(
            # OCR設定の最適化
            ocr_config=documentai.OcrConfig(
                enable_native_pdf_parsing=True,  # ネイティブPDF解析を有効化
                enable_image_quality_scores=True,  # 画像品質スコア
                enable_symbol=True,  # シンボル検出
                premium_features=documentai.OcrConfig.PremiumFeatures(
                    enable_selection_mark_detection=True,  # 選択マーク検出
                    compute_style_info=True,  # スタイル情報計算
                    enable_math_ocr=False  # 数式OCRは無効（パフォーマンス向上）
                )
            )
        )
    
    def analyze_document_with_ocr(self):
        """Document OCRプロセッサによる座標付き文書解析"""
        
        print("🔍 Document OCR 座標付き解析開始")
        print("=" * 60)
        
        results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processor_type": "Document OCR",
            "processor_id": self.config["ocr_processor_id"],
            "full_text": "",
            "text_blocks": [],
            "visual_elements": [],
            "extracted_figures": [],
            "page_images": [],
            "summary": {
                "total_pages": 0,
                "total_blocks": 0,
                "total_figures": 0,
                "coordinates_found": 0,
                "images_saved": 0
            }
        }
        
        try:
            # 🔹 1. PDF読み込み
            pdf_path = Path(self.config["pdf_path"])
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_path}")
            
            with open(pdf_path, "rb") as pdf_file:
                pdf_content = pdf_file.read()
            
            print(f"📁 PDF読み込み: {pdf_path.name} ({len(pdf_content):,} bytes)")
            
            # 🔹 2. Document OCR実行
            processor_name = self.client.processor_path(
                self.config["project_id"], 
                self.config["location"], 
                self.config["ocr_processor_id"]
            )
            
            raw_document = documentai.RawDocument(
                content=pdf_content, 
                mime_type="application/pdf"
            )
            
            print("🚀 Document OCR 実行中...")
            
            # ProcessOptionsを適用
            process_options = self.get_process_options()
            
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document,
                process_options=process_options
            )
            
            # Document AI実行
            result = self.client.process_document(request=request)
            document = result.document
            
            print("✅ Document OCR 処理完了\n")
            
            # 🔹 3. 全体テキスト取得
            results["full_text"] = document.text
            print(f"📄 全テキスト取得: {len(document.text):,}文字")
            
            # 🔹 4. ページ別詳細解析
            if hasattr(document, 'pages') and document.pages:
                results["summary"]["total_pages"] = len(document.pages)
                print(f"📋 ページ数: {len(document.pages)}個\n")
                
                for page_idx, page in enumerate(document.pages):
                    print(f"--- ページ {page_idx + 1} 解析 ---")
                    
                    # 🎯 4-1. テキストブロックと座標抽出
                    if hasattr(page, 'blocks') and page.blocks:
                        print(f"📝 テキストブロック: {len(page.blocks)}個")
                        
                        for block_idx, block in enumerate(page.blocks):
                            block_data = self._extract_text_block_with_coordinates(
                                block, document.text, page_idx + 1, block_idx + 1
                            )
                            if block_data:
                                results["text_blocks"].append(block_data)
                                results["summary"]["total_blocks"] += 1
                                if block_data["coordinates"]:
                                    results["summary"]["coordinates_found"] += 1
                                
                                print(f"  ブロック{block_idx + 1}: '{block_data['text'][:30]}...' "
                                      f"座標: {'✅' if block_data['coordinates'] else '❌'}")
                    
                    # 🎯 4-2. 画像・図表要素と座標抽出（詳細調査付き）
                    print(f"\n🔍 visual_elements 詳細調査:")
                    
                    if hasattr(page, 'visual_elements'):
                        visual_elements = page.visual_elements
                        print(f"   visual_elements属性: 存在")
                        print(f"   visual_elements型: {type(visual_elements)}")
                        print(f"   visual_elements長さ: {len(visual_elements) if visual_elements else 0}")
                        
                        if visual_elements and len(visual_elements) > 0:
                            print(f"🖼️ 視覚的要素: {len(visual_elements)}個")
                            
                            for elem_idx, element in enumerate(visual_elements):
                                print(f"\n   要素{elem_idx + 1} 詳細:")
                                print(f"     タイプ: {type(element)}")
                                
                                # 要素の全属性を調査
                                elem_attrs = [attr for attr in dir(element) if not attr.startswith('_')]
                                print(f"     利用可能属性: {elem_attrs}")
                                
                                # タイプ属性の詳細調査
                                if hasattr(element, 'type'):
                                    elem_type = str(element.type)
                                    print(f"     要素タイプ: {elem_type}")
                                else:
                                    print(f"     要素タイプ: 不明")
                                
                                # レイアウト情報の調査
                                if hasattr(element, 'layout'):
                                    layout = element.layout
                                    print(f"     レイアウト: 存在 ({type(layout)})")
                                    if hasattr(layout, 'bounding_poly'):
                                        print(f"     座標情報: 存在")
                                    else:
                                        print(f"     座標情報: なし")
                                else:
                                    print(f"     レイアウト: なし")
                                
                                # データ抽出実行
                                elem_data = self._extract_visual_element_with_coordinates(
                                    element, page_idx + 1, elem_idx + 1
                                )
                                if elem_data:
                                    results["visual_elements"].append(elem_data)
                                    
                                    if elem_data["type"] == "figure":
                                        results["summary"]["total_figures"] += 1
                                        print(f"     ✅ 図表として認識: '{elem_data['type']}'")
                                    else:
                                        print(f"     📊 その他要素: '{elem_data['type']}'")
                        else:
                            print(f"   ⚠️ visual_elements配列は存在するが空です")
                            
                            # 🔍 代替検出方法: blocks内の画像要素を調査
                            print(f"\n🔄 代替検出: blocksから画像要素を探索")
                            self._investigate_image_blocks_in_text_blocks(page, results, page_idx + 1)
                            
                            # 🔍 追加調査: ページ全体から視覚的領域を推定
                            print(f"\n🔍 追加調査: 視覚的領域推定")
                            self._estimate_visual_regions_from_text_gaps(page, results, page_idx + 1)
                            
                            # 🎯 キーワード検索による推定画像エリア抽出
                            print(f"\n🎯 キーワード検索: 椅子関連テキストから画像エリアを推定")
                            self._extract_estimated_image_areas_by_keywords(page, results, page_idx + 1, document.text)
                    else:
                        print(f"   ❌ visual_elements属性が存在しません")
                    
                    # 🎯 4-3. ページ画像保存
                    if hasattr(page, 'image') and page.image:
                        page_image_info = self._save_page_image(page, page_idx + 1)
                        if page_image_info:
                            results["page_images"].append(page_image_info)
                            results["summary"]["images_saved"] += 1
                            print(f"💾 ページ画像保存: {page_image_info['filename']}")
                    
                    print()  # 空行
            
            # 🔹 5. 図表の個別切り抜き実行
            print("🔄 図表切り抜き処理開始...")
            self._extract_figure_images(results)
            
            # 🔹 6. 結果サマリー表示
            self._display_summary(results)
            
            # 🔹 7. 結果をJSONファイルに保存
            output_file = f"document_ocr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"💾 結果保存完了: {output_file}")
            
            return results
            
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            return None
    
    def _extract_text_block_with_coordinates(self, block, full_text: str, page_num: int, block_num: int) -> Dict[str, Any]:
        """テキストブロックから座標付きデータを抽出"""
        
        block_data = {
            "page": page_num,
            "block_id": block_num,
            "text": "",
            "coordinates": [],
            "bounding_box": {}
        }
        
        try:
            # テキスト内容取得
            if hasattr(block, 'layout') and hasattr(block.layout, 'text_anchor'):
                text_anchor = block.layout.text_anchor
                if hasattr(text_anchor, 'text_segments'):
                    for segment in text_anchor.text_segments:
                        start_idx = int(segment.start_index) if hasattr(segment, 'start_index') else 0
                        end_idx = int(segment.end_index) if hasattr(segment, 'end_index') else 0
                        block_data["text"] += full_text[start_idx:end_idx]
            
            # 座標情報取得
            if hasattr(block, 'layout') and hasattr(block.layout, 'bounding_poly'):
                bounding_poly = block.layout.bounding_poly
                if hasattr(bounding_poly, 'normalized_vertices'):
                    coordinates = []
                    for vertex in bounding_poly.normalized_vertices:
                        if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                            coordinates.append({
                                "x": float(vertex.x),
                                "y": float(vertex.y)
                            })
                    
                    if len(coordinates) >= 4:
                        block_data["coordinates"] = coordinates
                        block_data["bounding_box"] = {
                            "left": coordinates[0]["x"],
                            "top": coordinates[0]["y"], 
                            "right": coordinates[2]["x"],
                            "bottom": coordinates[2]["y"],
                            "width": coordinates[2]["x"] - coordinates[0]["x"],
                            "height": coordinates[2]["y"] - coordinates[0]["y"]
                        }
            
            return block_data if block_data["text"].strip() else None
            
        except Exception as e:
            print(f"⚠️ ブロック{block_num}の処理でエラー: {e}")
            return None
    
    def _extract_visual_element_with_coordinates(self, element, page_num: int, elem_num: int) -> Dict[str, Any]:
        """視覚的要素から座標付きデータを抽出"""
        
        elem_data = {
            "page": page_num,
            "element_id": elem_num,
            "type": "unknown",
            "coordinates": [],
            "bounding_box": {}
        }
        
        try:
            # 要素タイプ取得
            if hasattr(element, 'type'):
                elem_data["type"] = str(element.type).lower()
            
            # 座標情報取得
            if hasattr(element, 'layout') and hasattr(element.layout, 'bounding_poly'):
                bounding_poly = element.layout.bounding_poly
                if hasattr(bounding_poly, 'normalized_vertices'):
                    coordinates = []
                    for vertex in bounding_poly.normalized_vertices:
                        if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                            coordinates.append({
                                "x": float(vertex.x),
                                "y": float(vertex.y)
                            })
                    
                    if len(coordinates) >= 4:
                        elem_data["coordinates"] = coordinates
                        elem_data["bounding_box"] = {
                            "left": coordinates[0]["x"],
                            "top": coordinates[0]["y"],
                            "right": coordinates[2]["x"], 
                            "bottom": coordinates[2]["y"],
                            "width": coordinates[2]["x"] - coordinates[0]["x"],
                            "height": coordinates[2]["y"] - coordinates[0]["y"]
                        }
            
            return elem_data if elem_data["coordinates"] else None
            
        except Exception as e:
            print(f"⚠️ 視覚要素{elem_num}の処理でエラー: {e}")
            return None
    
    def _investigate_image_blocks_in_text_blocks(self, page, results: Dict[str, Any], page_num: int):
        """テキストブロック内から画像要素を代替検出"""
        
        try:
            if not hasattr(page, 'blocks') or not page.blocks:
                print(f"   blocks属性なし")
                return
            
            image_blocks_found = 0
            
            for block_idx, block in enumerate(page.blocks):
                # ブロックの詳細調査
                block_attrs = [attr for attr in dir(block) if not attr.startswith('_')]
                
                # 画像関連属性の検索
                has_image_attrs = any(attr in ['image', 'visual', 'figure'] for attr in [attr.lower() for attr in block_attrs])
                
                # レイアウトのtext_anchorがない場合は画像ブロックの可能性
                has_text_content = False
                if hasattr(block, 'layout') and hasattr(block.layout, 'text_anchor'):
                    text_anchor = block.layout.text_anchor
                    if hasattr(text_anchor, 'text_segments') and text_anchor.text_segments:
                        has_text_content = len(text_anchor.text_segments) > 0
                
                # 座標のみでテキストなしの場合は画像の可能性
                if (hasattr(block, 'layout') and 
                    hasattr(block.layout, 'bounding_poly') and 
                    not has_text_content):
                    
                    print(f"     🖼️ 候補ブロック{block_idx + 1}: テキストなし、座標あり")
                    
                    # 画像ブロックとして処理
                    image_block_data = {
                        "page": page_num,
                        "element_id": f"block_{block_idx + 1}",
                        "type": "potential_image",
                        "source": "text_blocks_analysis",
                        "coordinates": [],
                        "bounding_box": {}
                    }
                    
                    # 座標抽出
                    bounding_poly = block.layout.bounding_poly
                    if hasattr(bounding_poly, 'normalized_vertices'):
                        coordinates = []
                        for vertex in bounding_poly.normalized_vertices:
                            if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                                coordinates.append({
                                    "x": float(vertex.x),
                                    "y": float(vertex.y)
                                })
                        
                        if len(coordinates) >= 4:
                            image_block_data["coordinates"] = coordinates
                            image_block_data["bounding_box"] = {
                                "left": coordinates[0]["x"],
                                "top": coordinates[0]["y"],
                                "right": coordinates[2]["x"],
                                "bottom": coordinates[2]["y"],
                                "width": coordinates[2]["x"] - coordinates[0]["x"],
                                "height": coordinates[2]["y"] - coordinates[0]["y"]
                            }
                            
                            # サイズフィルタ（極小要素を除外）
                            area = image_block_data["bounding_box"]["width"] * image_block_data["bounding_box"]["height"]
                            if area > 0.001:  # 0.1%以上のサイズ
                                results["visual_elements"].append(image_block_data)
                                image_blocks_found += 1
                                print(f"     ✅ 画像候補として追加: サイズ{image_block_data['bounding_box']['width']:.3f}x{image_block_data['bounding_box']['height']:.3f}")
            
            if image_blocks_found > 0:
                print(f"   📊 代替検出成功: {image_blocks_found}個の画像候補を発見")
                results["summary"]["total_figures"] += image_blocks_found
            else:
                print(f"   ❌ 代替検出でも画像要素は見つかりませんでした")
                
        except Exception as e:
            print(f"   ⚠️ 代替検出でエラー: {e}")
    
    def _estimate_visual_regions_from_text_gaps(self, page, results: Dict[str, Any], page_num: int):
        """テキストの配置間隙から視覚的領域を推定"""
        
        try:
            if not hasattr(page, 'blocks') or not page.blocks:
                print(f"   blocks属性なし")
                return
            
            # テキストブロックの座標を収集
            text_regions = []
            for block in page.blocks:
                if (hasattr(block, 'layout') and 
                    hasattr(block.layout, 'bounding_poly') and
                    hasattr(block.layout, 'text_anchor')):
                    
                    # テキストがあるブロックの座標を記録
                    bounding_poly = block.layout.bounding_poly
                    if hasattr(bounding_poly, 'normalized_vertices') and len(bounding_poly.normalized_vertices) >= 4:
                        vertices = bounding_poly.normalized_vertices
                        text_regions.append({
                            "left": float(vertices[0].x),
                            "top": float(vertices[0].y),
                            "right": float(vertices[2].x),
                            "bottom": float(vertices[2].y)
                        })
            
            if len(text_regions) < 2:
                print(f"   テキスト領域が不足（{len(text_regions)}個）- 推定不可")
                return
            
            print(f"   📝 テキスト領域: {len(text_regions)}個を分析")
            
            # ページを格子状に分割して空白領域を検出
            grid_size = 20  # 20x20グリッドに細分化
            potential_image_areas = []
            
            for row in range(grid_size):
                for col in range(grid_size):
                    # グリッド座標
                    grid_left = col / grid_size
                    grid_top = row / grid_size
                    grid_right = (col + 1) / grid_size
                    grid_bottom = (row + 1) / grid_size
                    
                    # このグリッドセルがテキスト領域と重複しているかチェック
                    overlaps_text = False
                    for text_region in text_regions:
                        if (grid_right > text_region["left"] and 
                            grid_left < text_region["right"] and 
                            grid_bottom > text_region["top"] and 
                            grid_top < text_region["bottom"]):
                            overlaps_text = True
                            break
                    
                    # テキストと重複していない場合は画像候補
                    if not overlaps_text:
                        potential_image_areas.append({
                            "left": grid_left,
                            "top": grid_top,
                            "right": grid_right,
                            "bottom": grid_bottom,
                            "width": 1.0 / grid_size,
                            "height": 1.0 / grid_size,
                            "area": (1.0 / grid_size) ** 2
                        })
            
            if not potential_image_areas:
                print(f"   ❌ 画像候補領域は見つかりませんでした")
                return
            
            # 隣接する領域を統合
            merged_areas = self._merge_adjacent_areas(potential_image_areas, grid_size)
            
            # 最小サイズフィルタ（0.2%以上、80%以下の領域のみ）
            significant_areas = [area for area in merged_areas 
                               if 0.002 <= area["area"] <= 0.8]
            
            if significant_areas:
                print(f"   ✅ 推定画像領域: {len(significant_areas)}個を発見")
                
                for i, area in enumerate(significant_areas):
                    estimated_figure = {
                        "page": page_num,
                        "element_id": f"estimated_{i + 1}",
                        "type": "estimated_figure",
                        "source": "text_gap_analysis",
                        "coordinates": [
                            {"x": area["left"], "y": area["top"]},
                            {"x": area["right"], "y": area["top"]},
                            {"x": area["right"], "y": area["bottom"]},
                            {"x": area["left"], "y": area["bottom"]}
                        ],
                        "bounding_box": {
                            "left": area["left"],
                            "top": area["top"],
                            "right": area["right"],
                            "bottom": area["bottom"],
                            "width": area["width"],
                            "height": area["height"]
                        }
                    }
                    
                    results["visual_elements"].append(estimated_figure)
                    results["summary"]["total_figures"] += 1
                    print(f"     📊 推定領域{i + 1}: サイズ{area['width']:.3f}x{area['height']:.3f} (面積{area['area']:.3f})")
            else:
                print(f"   ⚠️ 十分な大きさの画像領域は見つかりませんでした")
                
        except Exception as e:
            print(f"   ⚠️ 視覚領域推定でエラー: {e}")
    
    def _merge_adjacent_areas(self, areas, grid_size):
        """隣接する領域を統合"""
        # 簡易的な統合（隣接チェックと結合）
        merged = []
        used = set()
        
        for i, area in enumerate(areas):
            if i in used:
                continue
            
            # この領域から開始して隣接領域を探索
            current_area = area.copy()
            used.add(i)
            
            # 隣接領域を統合
            changed = True
            while changed:
                changed = False
                for j, other_area in enumerate(areas):
                    if j in used:
                        continue
                    
                    # 隣接チェック（簡易版）
                    if (abs(current_area["right"] - other_area["left"]) < 1/grid_size * 1.1 or
                        abs(current_area["left"] - other_area["right"]) < 1/grid_size * 1.1 or
                        abs(current_area["bottom"] - other_area["top"]) < 1/grid_size * 1.1 or
                        abs(current_area["top"] - other_area["bottom"]) < 1/grid_size * 1.1):
                        
                        # 領域を統合
                        current_area["left"] = min(current_area["left"], other_area["left"])
                        current_area["top"] = min(current_area["top"], other_area["top"])
                        current_area["right"] = max(current_area["right"], other_area["right"])
                        current_area["bottom"] = max(current_area["bottom"], other_area["bottom"])
                        current_area["width"] = current_area["right"] - current_area["left"]
                        current_area["height"] = current_area["bottom"] - current_area["top"]
                        current_area["area"] = current_area["width"] * current_area["height"]
                        
                        used.add(j)
                        changed = True
            
            merged.append(current_area)
        
        return merged
    
    def _extract_estimated_image_areas_by_keywords(self, page, results: Dict[str, Any], page_num: int, full_text: str):
        """キーワード検索による推定画像エリア抽出"""
        
        try:
            if not hasattr(page, 'blocks') or not page.blocks:
                print(f"   blocks属性なし")
                return
            
            keyword_blocks_found = 0
            
            for keyword in self.chair_keywords:
                print(f"\n   🔍 キーワード検索: '{keyword}'")
                
                # キーワードを含むブロックを検索
                matching_blocks = []
                
                for block_idx, block in enumerate(page.blocks):
                    # ブロックのテキスト内容を取得
                    block_text = ""
                    if (hasattr(block, 'layout') and 
                        hasattr(block.layout, 'text_anchor') and
                        block.layout.text_anchor.text_segments):
                        
                        for segment in block.layout.text_anchor.text_segments:
                            start_idx = int(segment.start_index) if hasattr(segment, 'start_index') else 0
                            end_idx = int(segment.end_index) if hasattr(segment, 'end_index') else 0
                            block_text += full_text[start_idx:end_idx]
                    
                    # キーワードマッチング
                    if keyword in block_text:
                        # 座標情報を取得
                        if (hasattr(block, 'layout') and 
                            hasattr(block.layout, 'bounding_poly') and
                            hasattr(block.layout.bounding_poly, 'normalized_vertices')):
                            
                            vertices = block.layout.bounding_poly.normalized_vertices
                            if len(vertices) >= 4:
                                block_coords = {
                                    'block_idx': block_idx + 1,
                                    'text': block_text.strip(),
                                    'keyword': keyword,
                                    'left': float(vertices[0].x),
                                    'top': float(vertices[0].y),
                                    'right': float(vertices[2].x),
                                    'bottom': float(vertices[2].y)
                                }
                                matching_blocks.append(block_coords)
                                print(f"     ✅ ブロック{block_idx + 1}で発見: '{block_text[:30]}...'")
                
                # マッチしたブロックがある場合、推定画像エリアを作成
                if matching_blocks:
                    for i, match in enumerate(matching_blocks):
                        estimated_area = self._create_estimated_image_area(match, keyword, i + 1)
                        
                        if estimated_area:
                            results["visual_elements"].append(estimated_area)
                            results["summary"]["total_figures"] += 1
                            keyword_blocks_found += 1
                            
                            print(f"     📊 推定画像エリア作成: {estimated_area['estimated_type']}")
                            print(f"        座標範囲: ({estimated_area['bounding_box']['left']:.3f}, {estimated_area['bounding_box']['top']:.3f}) → ({estimated_area['bounding_box']['right']:.3f}, {estimated_area['bounding_box']['bottom']:.3f})")
                else:
                    print(f"     ❌ '{keyword}' を含むブロックが見つかりません")
            
            if keyword_blocks_found > 0:
                print(f"\n   🎯 キーワード検索結果: {keyword_blocks_found}個の推定画像エリアを作成")
            else:
                print(f"\n   ⚠️ キーワード検索でも推定エリアは見つかりませんでした")
                
        except Exception as e:
            print(f"   ⚠️ キーワード検索でエラー: {e}")
    
    def _create_estimated_image_area(self, text_block: Dict, keyword: str, instance_num: int) -> Optional[Dict[str, Any]]:
        """テキストブロック座標から推定画像エリアを作成"""
        
        try:
            # テキストブロックの中心座標を計算
            text_center_x = (text_block['left'] + text_block['right']) / 2
            text_center_y = (text_block['top'] + text_block['bottom']) / 2
            
            # オフセットを適用して推定エリアを計算
            estimated_left = max(0.0, text_center_x - self.area_offset['left'])
            estimated_right = min(1.0, text_center_x + self.area_offset['right'])
            estimated_top = max(0.0, text_center_y - self.area_offset['top'])
            estimated_bottom = min(1.0, text_center_y + self.area_offset['bottom'])
            
            # 推定画像エリアデータを作成
            estimated_area = {
                "page": 1,
                "element_id": f"keyword_{keyword}_{instance_num}",
                "type": "estimated_figure",
                "source": "keyword_search",
                "estimated_type": f"{keyword}_area",
                "text_reference": {
                    "block_idx": text_block['block_idx'],
                    "keyword": keyword,
                    "text_content": text_block['text']
                },
                "coordinates": [
                    {"x": estimated_left, "y": estimated_top},
                    {"x": estimated_right, "y": estimated_top},
                    {"x": estimated_right, "y": estimated_bottom},
                    {"x": estimated_left, "y": estimated_bottom}
                ],
                "bounding_box": {
                    "left": estimated_left,
                    "top": estimated_top,
                    "right": estimated_right,
                    "bottom": estimated_bottom,
                    "width": estimated_right - estimated_left,
                    "height": estimated_bottom - estimated_top
                }
            }
            
            return estimated_area
            
        except Exception as e:
            print(f"   ⚠️ 推定エリア作成でエラー: {e}")
            return None
            
            keyword_blocks_found = 0
            
            for keyword in self.chair_keywords:
                print(f"\n   🔍 キーワード検索: '{keyword}'")
                
                # キーワードを含むブロックを検索
                matching_blocks = []
                
                for block_idx, block in enumerate(page.blocks):
                    # ブロックのテキスト内容を取得
                    block_text = ""
                    if (hasattr(block, 'layout') and 
                        hasattr(block.layout, 'text_anchor') and
                        block.layout.text_anchor.text_segments):
                        
                        for segment in block.layout.text_anchor.text_segments:
                            start_idx = int(segment.start_index) if hasattr(segment, 'start_index') else 0
                            end_idx = int(segment.end_index) if hasattr(segment, 'end_index') else 0
                            block_text += full_text[start_idx:end_idx]
                    
                    # キーワードマッチング
                    if keyword in block_text:
                        # 座標情報を取得
                        if (hasattr(block, 'layout') and 
                            hasattr(block.layout, 'bounding_poly') and
                            hasattr(block.layout.bounding_poly, 'normalized_vertices')):
                            
                            vertices = block.layout.bounding_poly.normalized_vertices
                            if len(vertices) >= 4:
                                block_coords = {
                                    'block_idx': block_idx + 1,
                                    'text': block_text.strip(),
                                    'keyword': keyword,
                                    'left': float(vertices[0].x),
                                    'top': float(vertices[0].y),
                                    'right': float(vertices[2].x),
                                    'bottom': float(vertices[2].y)
                                }
                                matching_blocks.append(block_coords)
                                print(f"     ✅ ブロック{block_idx + 1}で発見: '{block_text[:30]}...'")
                
                # マッチしたブロックがある場合、推定画像エリアを作成
                if matching_blocks:
                    for i, match in enumerate(matching_blocks):
                        estimated_area = self._create_estimated_image_area(match, keyword, i + 1)
                        
                        if estimated_area:
                            results["visual_elements"].append(estimated_area)
                            results["summary"]["total_figures"] += 1
                            keyword_blocks_found += 1
                            
                            print(f"     📊 推定画像エリア作成: {estimated_area['estimated_type']}")
                            print(f"        座標範囲: ({estimated_area['bounding_box']['left']:.3f}, {estimated_area['bounding_box']['top']:.3f}) → ({estimated_area['bounding_box']['right']:.3f}, {estimated_area['bounding_box']['bottom']:.3f})")
                else:
                    print(f"     ❌ '{keyword}' を含むブロックが見つかりません")
            
            if keyword_blocks_found > 0:
                print(f"\n   🎯 キーワード検索結果: {keyword_blocks_found}個の推定画像エリアを作成")
            else:
                print(f"\n   ⚠️ キーワード検索でも推定エリアは見つかりませんでした")
                
        except Exception as e:
            print(f"   ⚠️ キーワード検索でエラー: {e}")
    
    def _create_estimated_image_area(self, text_block: Dict, keyword: str, instance_num: int) -> Optional[Dict[str, Any]]:
        """テキストブロック座標から推定画像エリアを作成"""
        
        try:
            # テキストブロックの中心座標を計算
            text_center_x = (text_block['left'] + text_block['right']) / 2
            text_center_y = (text_block['top'] + text_block['bottom']) / 2
            
            # オフセットを適用して推定エリアを計算
            estimated_left = max(0.0, text_center_x - self.area_offset['left'])
            estimated_right = min(1.0, text_center_x + self.area_offset['right'])
            estimated_top = max(0.0, text_center_y - self.area_offset['top'])
            estimated_bottom = min(1.0, text_center_y + self.area_offset['bottom'])
            
            # 推定画像エリアデータを作成
            estimated_area = {
                "page": 1,
                "element_id": f"keyword_{keyword}_{instance_num}",
                "type": "estimated_figure",
                "source": "keyword_search",
                "estimated_type": f"{keyword}_area",
                "text_reference": {
                    "block_idx": text_block['block_idx'],
                    "keyword": keyword,
                    "text_content": text_block['text']
                },
                "coordinates": [
                    {"x": estimated_left, "y": estimated_top},
                    {"x": estimated_right, "y": estimated_top},
                    {"x": estimated_right, "y": estimated_bottom},
                    {"x": estimated_left, "y": estimated_bottom}
                ],
                "bounding_box": {
                    "left": estimated_left,
                    "top": estimated_top,
                    "right": estimated_right,
                    "bottom": estimated_bottom,
                    "width": estimated_right - estimated_left,
                    "height": estimated_bottom - estimated_top
                }
            }
            
            return estimated_area
            
        except Exception as e:
            print(f"   ⚠️ 推定エリア作成でエラー: {e}")
            return None
    
    def _save_page_image(self, page, page_num: int) -> Optional[Dict[str, Any]]:
        """ページ画像をBase64からデコードして保存"""
        
        try:
            if hasattr(page, 'image') and hasattr(page.image, 'content'):
                # Base64デコード
                image_bytes = page.image.content
                image = Image.open(io.BytesIO(image_bytes))
                
                # 画像保存
                filename = f"page_{page_num:02d}.png"
                filepath = Path(self.config["output_dir"]) / filename
                image.save(filepath, "PNG")
                
                return {
                    "page": page_num,
                    "filename": filename,
                    "filepath": str(filepath),
                    "width": image.width,
                    "height": image.height,
                    "size_mb": round(len(image_bytes) / 1024 / 1024, 2)
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️ ページ{page_num}画像保存でエラー: {e}")
            return None
    
    def _extract_figure_images(self, results: Dict[str, Any]):
        """座標情報を使用してページ画像から図表を切り抜き"""
        
        extracted_count = 0
        
        try:
            # 図表要素のみをフィルタリング（推定図表も含む）
            figure_elements = [elem for elem in results["visual_elements"] 
                             if elem["type"] in ["figure", "estimated_figure", "potential_image"]]
            
            if not figure_elements:
                print("📊 切り抜き対象の図表が見つかりませんでした")
                return
            
            print(f"📊 {len(figure_elements)}個の図表切り抜きを開始...")
            print("   対象タイプ:", [elem["type"] for elem in figure_elements])
            
            # ページ画像と図表の対応付け
            for figure in figure_elements:
                page_num = figure["page"]
                
                # 対応するページ画像を検索
                page_image = next(
                    (img for img in results["page_images"] if img["page"] == page_num), 
                    None
                )
                
                if not page_image:
                    print(f"⚠️ ページ{page_num}の画像が見つかりません")
                    continue
                
                # 画像切り抜き実行
                cropped_info = self._crop_figure_from_page(figure, page_image)
                if cropped_info:
                    results["extracted_figures"].append(cropped_info)
                    extracted_count += 1
                    print(f"✅ 図表切り抜き成功: {cropped_info['filename']}")
            
            results["summary"]["total_figures"] = extracted_count
            print(f"🎯 図表切り抜き完了: {extracted_count}個")
            
        except Exception as e:
            print(f"❌ 図表切り抜き処理でエラー: {e}")
    
    def _crop_figure_from_page(self, figure: Dict[str, Any], page_image: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ページ画像から指定座標の図表を切り抜き"""
        
        try:
            # ページ画像を開く
            page_img = Image.open(page_image["filepath"])
            page_width, page_height = page_img.size
            
            # 正規化座標を実際のピクセル座標に変換
            bbox = figure["bounding_box"]
            left = int(bbox["left"] * page_width)
            top = int(bbox["top"] * page_height)
            right = int(bbox["right"] * page_width)
            bottom = int(bbox["bottom"] * page_height)
            
            # 切り抜き実行
            cropped_img = page_img.crop((left, top, right, bottom))
            
            # 保存ファイル名を生成（推定エリアの場合は特別な命名）
            if figure.get('source') == 'keyword_search':
                filename = f"estimated_{figure['estimated_type']}_page{figure['page']:02d}.png"
            else:
                filename = f"figure_page{figure['page']:02d}_elem{figure['element_id']}.png"
            
            filepath = Path(self.config["output_dir"]) / filename
            cropped_img.save(filepath, "PNG")
            
            return {
                "page": figure["page"],
                "element_id": figure["element_id"],
                "filename": filename,
                "filepath": str(filepath),
                "original_coordinates": figure["coordinates"],
                "pixel_coordinates": {
                    "left": left,
                    "top": top,
                    "right": right,
                    "bottom": bottom
                },
                "width": right - left,
                "height": bottom - top
            }
            
        except Exception as e:
            print(f"⚠️ 図表切り抜きでエラー: {e}")
            return None
    
    def _investigate_image_blocks_in_text_blocks(self, page, results: Dict[str, Any], page_num: int):
        """テキストブロック内から画像要素を代替検出"""
        
        try:
            if not hasattr(page, 'blocks') or not page.blocks:
                print(f"   blocks属性なし")
                return
            
            image_blocks_found = 0
            
            for block_idx, block in enumerate(page.blocks):
                # ブロックの詳細調査
                block_attrs = [attr for attr in dir(block) if not attr.startswith('_')]
                
                # 画像関連属性の検索
                has_image_attrs = any(attr in ['image', 'visual', 'figure'] for attr in [attr.lower() for attr in block_attrs])
                
                # レイアウトのtext_anchorがない場合は画像ブロックの可能性
                has_text_content = False
                if hasattr(block, 'layout') and hasattr(block.layout, 'text_anchor'):
                    text_anchor = block.layout.text_anchor
                    if hasattr(text_anchor, 'text_segments') and text_anchor.text_segments:
                        has_text_content = len(text_anchor.text_segments) > 0
                
                # 座標のみでテキストなしの場合は画像の可能性
                if (hasattr(block, 'layout') and 
                    hasattr(block.layout, 'bounding_poly') and 
                    not has_text_content):
                    
                    print(f"     🖼️ 候補ブロック{block_idx + 1}: テキストなし、座標あり")
                    
                    # 画像ブロックとして処理
                    image_block_data = {
                        "page": page_num,
                        "element_id": f"block_{block_idx + 1}",
                        "type": "potential_image",
                        "source": "text_blocks_analysis",
                        "coordinates": [],
                        "bounding_box": {}
                    }
                    
                    # 座標抽出
                    bounding_poly = block.layout.bounding_poly
                    if hasattr(bounding_poly, 'normalized_vertices'):
                        coordinates = []
                        for vertex in bounding_poly.normalized_vertices:
                            if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                                coordinates.append({
                                    "x": float(vertex.x),
                                    "y": float(vertex.y)
                                })
                        
                        if len(coordinates) >= 4:
                            image_block_data["coordinates"] = coordinates
                            image_block_data["bounding_box"] = {
                                "left": coordinates[0]["x"],
                                "top": coordinates[0]["y"],
                                "right": coordinates[2]["x"],
                                "bottom": coordinates[2]["y"],
                                "width": coordinates[2]["x"] - coordinates[0]["x"],
                                "height": coordinates[2]["y"] - coordinates[0]["y"]
                            }
                            
                            # サイズフィルタ（極小要素を除外）
                            area = image_block_data["bounding_box"]["width"] * image_block_data["bounding_box"]["height"]
                            if area > 0.001:  # 0.1%以上のサイズ
                                results["visual_elements"].append(image_block_data)
                                image_blocks_found += 1
                                print(f"     ✅ 画像候補として追加: サイズ{image_block_data['bounding_box']['width']:.3f}x{image_block_data['bounding_box']['height']:.3f}")
            
            if image_blocks_found > 0:
                print(f"   📊 代替検出成功: {image_blocks_found}個の画像候補を発見")
                results["summary"]["total_figures"] += image_blocks_found
            else:
                print(f"   ❌ 代替検出でも画像要素は見つかりませんでした")
                
        except Exception as e:
            print(f"   ⚠️ 代替検出でエラー: {e}")
    
    def _display_summary(self, results: Dict[str, Any]):
        """結果サマリーを表示"""
        
        print("\n" + "=" * 60)
        print("📊 Document OCR 解析結果サマリー")
        print("=" * 60)
        
        summary = results["summary"]
        
        print(f"📄 全文字数: {len(results['full_text']):,}文字")
        print(f"📋 ページ数: {summary['total_pages']}個")
        print(f"📝 テキストブロック: {summary['total_blocks']}個")
        print(f"🎯 座標取得成功: {summary['coordinates_found']}個")
        print(f"🖼️ 図表要素: {summary['total_figures']}個")
        print(f"💾 画像保存: {summary['images_saved']}個")
        
        if results["extracted_figures"]:
            print(f"\n✅ 切り抜き成功した図表:")
            for figure in results["extracted_figures"]:
                print(f"  - {figure['filename']} ({figure['width']}x{figure['height']}px)")


def main():
    """メイン実行関数"""
    print("🚀 Google Cloud Document AI - Document OCR プロセッサ")
    print("座標付きテキスト抽出 & 画像切り抜きスクリプト")
    print("=" * 60)
    
    processor = DocumentOCRProcessor()
    results = processor.analyze_document_with_ocr()
    
    if results:
        print("\n🎉 処理が正常に完了しました！")
        print(f"📁 出力ディレクトリ: {processor.config['output_dir']}")
    else:
        print("\n❌ 処理中にエラーが発生しました")


if __name__ == "__main__":
    main()